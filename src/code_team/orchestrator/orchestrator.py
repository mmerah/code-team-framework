import asyncio
import os
import subprocess
from pathlib import Path

import yaml
from rich.live import Live
from rich.progress import Progress, TaskID
from rich.table import Table

from code_team.agents.base import Agent
from code_team.agents.coder import Coder
from code_team.agents.committer import Committer
from code_team.agents.plan_verifier import PlanVerifier
from code_team.agents.planner import Planner
from code_team.agents.prompter import Prompter
from code_team.agents.verifiers import CodeVerifier
from code_team.models.config import CodeTeamConfig
from code_team.models.plan import Plan, Task
from code_team.orchestrator.state import OrchestratorState
from code_team.utils import filesystem, git, llm, templates
from code_team.utils.ui import display, interactive


class Orchestrator:
    """Manages the state machine and coordinates agents."""

    def __init__(self, project_root: Path, config_path: Path):
        self.project_root = project_root
        self.config = self._load_config(config_path)
        self.state = OrchestratorState.IDLE
        self.plan_dir = self.project_root / self.config.paths.plan_dir
        self.report_dir = self.project_root / self.config.paths.report_dir

        self.llm_provider = llm.LLMProvider(self.config.llm, str(project_root))
        self.template_manager = templates.TemplateManager(
            project_root / self.config.paths.template_dir,
            project_root=project_root,
            guideline_files=self.config.templates.guideline_files,
            exclude_dirs=self.config.templates.exclude_dirs,
        )

        self._ensure_dirs_exist()

    def _load_config(self, path: Path) -> CodeTeamConfig:
        content = filesystem.read_file(path)
        if not content:
            raise FileNotFoundError("Config file not found.")
        return CodeTeamConfig.model_validate(yaml.safe_load(content))

    def _ensure_dirs_exist(self) -> None:
        self.plan_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _create_agent(self, agent_class: type[Agent]) -> Agent:
        """Factory method to create agents with consistent configuration."""
        return agent_class(
            self.llm_provider, self.template_manager, self.config, self.project_root
        )

    async def run_plan_phase(self, initial_request: str) -> None:
        """Runs the planning phase of the workflow."""
        self.state = OrchestratorState.PLANNING_DRAFTING
        plan_id = f"plan-{len(list(self.plan_dir.iterdir())) + 1:04d}"
        planner = self._create_agent(Planner)
        plan_files = await planner.run(initial_request=initial_request, plan_id=plan_id)

        if not plan_files:
            self.state = OrchestratorState.HALTED_FOR_ERROR
            display.error("Failed to generate plan files.")
            return

        current_plan_dir = self.plan_dir / plan_id
        current_plan_dir.mkdir()

        filesystem.write_file(current_plan_dir / "plan.yml", plan_files["plan.yml"])
        filesystem.write_file(
            current_plan_dir / "ACCEPTANCE_CRITERIA.md",
            plan_files["ACCEPTANCE_CRITERIA.md"],
        )

        self.state = OrchestratorState.PLANNING_AWAITING_REVIEW
        display.success(f"Plan '{plan_id}' created in {current_plan_dir}")
        display.info(
            f"Please review the files in {current_plan_dir}/ and edit them if needed."
        )

        # Simple interactive loop for plan review
        while self.state == OrchestratorState.PLANNING_AWAITING_REVIEW:
            user_input = interactive.get_menu_choice(
                "Review the plan and choose an action:",
                ["Accept plan", "Discuss revisions with Planner", "Run Plan Verifier"],
            )
            if user_input == "Accept plan":
                display.success("Plan accepted. You can now run the coding phase.")
                break
            elif user_input == "Discuss revisions with Planner":
                await self._discuss_plan_revisions(current_plan_dir)
            elif user_input == "Run Plan Verifier":
                await self._verify_plan(current_plan_dir)

    async def _discuss_plan_revisions(self, plan_dir: Path) -> None:
        """Allow user to discuss plan revisions with the Planner."""
        self.state = OrchestratorState.PLANNING_DRAFTING

        # Get user feedback for revision
        revision_request = interactive.get_text_input(
            "Describe what you'd like to revise about the plan:"
        )

        if not revision_request.strip():
            display.warning("No revision request provided. Returning to plan review.")
            self.state = OrchestratorState.PLANNING_AWAITING_REVIEW
            return

        # Re-run planner with revision request
        planner = self._create_agent(Planner)
        plan_files = await planner.run(
            initial_request=revision_request, plan_id=plan_dir.name
        )

        if not plan_files:
            display.error("Failed to generate revised plan.")
            self.state = OrchestratorState.PLANNING_AWAITING_REVIEW
            return

        # Update the existing plan files
        filesystem.write_file(plan_dir / "plan.yml", plan_files["plan.yml"])
        filesystem.write_file(
            plan_dir / "ACCEPTANCE_CRITERIA.md",
            plan_files["ACCEPTANCE_CRITERIA.md"],
        )

        display.success("Plan has been revised based on your feedback.")
        self.state = OrchestratorState.PLANNING_AWAITING_REVIEW

    async def _verify_plan(self, plan_dir: Path) -> None:
        self.state = OrchestratorState.PLANNING_VERIFYING
        verifier = self._create_agent(PlanVerifier)

        plan_content = filesystem.read_file(plan_dir / "plan.yml") or ""
        criteria_content = (
            filesystem.read_file(plan_dir / "ACCEPTANCE_CRITERIA.md") or ""
        )

        feedback = await verifier.run(
            plan_content=plan_content, acceptance_criteria=criteria_content
        )
        filesystem.write_file(plan_dir / "FEEDBACK.md", feedback)

        display.panel(feedback, title="Plan Verification Feedback")

        self.state = OrchestratorState.PLANNING_AWAITING_REVIEW
        display.info("You can now revise the plan manually or accept the plan.")

    async def run_code_phase(self) -> None:
        """Runs the main coding and verification loop."""
        plan = self._select_plan_interactively()
        if not plan:
            display.error("No plan selected. Please run the planning phase first.")
            return

        # Count pending tasks for progress tracking
        pending_tasks = [t for t in plan.tasks if t.status == "pending"]
        total_tasks = len(pending_tasks)

        if total_tasks == 0:
            display.success("🎉 All tasks are already completed!")
            return

        # Create single progress bar for the entire coding phase
        progress = Progress()

        with Live(progress, refresh_per_second=10):
            # Add overall task tracking
            overall_task = progress.add_task(
                f"[progress]Executing {total_tasks} tasks...[/progress]",
                total=total_tasks,
            )

            # Add current task tracking
            current_task = progress.add_task(
                "[progress]Preparing...[/progress]",
                total=3,  # prompting, coding, verifying
            )

            self.state = OrchestratorState.CODING_AWAITING_TASK_SELECTION
            while self.state not in [
                OrchestratorState.PLAN_COMPLETE,
                OrchestratorState.HALTED_FOR_ERROR,
            ]:
                task_id = self._select_next_task(plan)
                if task_id == "PLAN_COMPLETE":
                    self.state = OrchestratorState.PLAN_COMPLETE
                    progress.update(overall_task, completed=total_tasks)
                    progress.update(
                        current_task,
                        description="[progress]Complete![/progress]",
                        completed=3,
                    )
                    display.success("🎉 Plan complete! All tasks have been finished.")
                    break

                task = next((t for t in plan.tasks if t.id == task_id), None)
                if not task:
                    self.state = OrchestratorState.HALTED_FOR_ERROR
                    display.error(f"Task '{task_id}' not found in plan.")
                    break

                # Reset current task progress
                progress.update(
                    current_task,
                    description=f"[progress]Working on {task.id}...[/progress]",
                    completed=0,
                )

                await self._execute_task_cycle(plan, task, progress, current_task)

                # Update overall progress
                completed_count = len(
                    [t for t in plan.tasks if t.status == "completed"]
                )
                progress.update(overall_task, completed=completed_count)

                # Reload plan to get updated task statuses
                plan = self._get_latest_plan()
                if not plan:
                    break

    async def _execute_task_cycle(
        self, plan: Plan, task: Task, progress: Progress, current_task_id: TaskID
    ) -> None:
        """Handles the full lifecycle for a single task, allowing for retries."""
        verification_feedback: str | None = None
        max_retries = 3
        current_try = 0

        # Load existing feedback from previous attempts if available
        report_file = self.report_dir / plan.plan_id / f"{task.id}.md"
        if report_file.exists():
            existing_report = filesystem.read_file(report_file) or ""
            if existing_report.strip():
                verification_feedback = (
                    f"--- Previous Verification Report ---\n{existing_report}"
                )

        while current_try < max_retries:
            current_try += 1

            # CODING
            self.state = OrchestratorState.CODING_PROMPTING
            progress.update(
                current_task_id,
                description=f"[progress]Preparing prompt for {task.id}...[/progress]",
                completed=0,
            )

            prompter = self._create_agent(Prompter)
            prompt_file_path = await prompter.run(task=task, plan_id=plan.plan_id)
            progress.update(current_task_id, completed=1)

            # Pause for user review
            display.info(
                f"Prompter has generated the instructions for the Coder. Please review the file: {prompt_file_path}"
            )
            user_choice = interactive.get_menu_choice(
                "Proceed with these instructions?",
                ["Proceed", "Edit instructions manually and then proceed"],
            )

            # User can edit the file manually if they choose to
            if user_choice == "Edit instructions manually and then proceed":
                display.info("Please edit the prompt file and press Enter when ready.")
                input()

            self.state = OrchestratorState.CODING_IN_PROGRESS
            progress.update(
                current_task_id,
                description=f"[progress]Coder working on {task.id}...[/progress]",
                completed=1,
            )

            coder = self._create_agent(Coder)
            # Pass the feedback from the previous loop iteration (if any)
            await coder.run(
                coder_prompt=prompt_file_path,
                verification_feedback=verification_feedback,
                plan_id=plan.plan_id,
            )
            progress.update(current_task_id, completed=2)

            # VERIFICATION
            self.state = OrchestratorState.VERIFYING
            progress.update(
                current_task_id,
                description=f"[progress]Verifying changes for {task.id}...[/progress]",
                completed=2,
            )

            verification_report = await self._run_verification(task)
            progress.update(current_task_id, completed=3)

            # Save verification report to file
            report_dir = self.report_dir / plan.plan_id
            report_dir.mkdir(parents=True, exist_ok=True)
            report_file = report_dir / f"{task.id}.md"
            filesystem.write_file(report_file, verification_report)

            self.state = OrchestratorState.AWAITING_VERIFICATION_REVIEW
            display.panel(verification_report, title="Verification Report")

            user_decision = await self._get_user_decision()

            if user_decision.lower().startswith("/accept_changes"):
                await self._commit_changes(plan, task)
                task.status = "completed"
                filesystem.save_plan(self.plan_dir / plan.plan_id / "plan.yml", plan)
                return  # Exit the loop and task cycle successfully

            elif user_decision.lower().startswith("/reject_changes"):
                feedback_text = user_decision.replace("/reject_changes", "").strip()

                # Load existing report content and append new feedback
                existing_content = ""
                if report_file.exists():
                    existing_content = filesystem.read_file(report_file) or ""

                combined_feedback = existing_content
                if feedback_text:
                    combined_feedback += f"\n\n--- User Feedback (Attempt {current_try}) ---\n{feedback_text}"

                # Update the report file with the new feedback
                filesystem.write_file(report_file, combined_feedback)

                verification_feedback = combined_feedback
                display.warning("Changes rejected. Rerunning Coder with feedback...")
                # The loop will continue to the next iteration
            else:
                display.error("Invalid command. Aborting task.")
                break  # Or handle as an error

        display.error(
            f"Task '{task.id}' failed after {max_retries} attempts. Manual intervention needed."
        )
        task.status = "failed"
        filesystem.save_plan(self.plan_dir / plan.plan_id / "plan.yml", plan)

    async def _run_verification(self, task: Task) -> str:
        """Runs all configured verification steps, including commands and agents."""
        diff = git.get_git_diff(self.project_root)
        reports: list[str] = []

        # Run automated commands
        command_reports: list[str] = []
        display.info("Running automated verification commands...")
        for cmd_config in self.config.verification.commands:
            try:
                result = subprocess.run(
                    cmd_config.command.split(),
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=False,  # Use False to capture output even on failure
                )
                status = "PASS" if result.returncode == 0 else "FAIL"
                report_line = f"- **{cmd_config.name}:** {status}"
                if status == "FAIL":
                    report_line += f"\n  ```\n{result.stdout}\n{result.stderr}\n  ```"
                command_reports.append(report_line)
            except Exception as e:
                command_reports.append(
                    f"- **{cmd_config.name}:** ERROR\n  ```\n{e}\n  ```"
                )

        if command_reports:
            reports.append("## Automated Checks\n\n" + "\n".join(command_reports))

        # Agent verifiers
        verifiers = self.config.verifier_instances.model_dump()
        for verifier_type, count in verifiers.items():
            if count > 0:
                verifier = CodeVerifier(
                    verifier_type,
                    self.llm_provider,
                    self.template_manager,
                    self.config,
                    self.project_root,
                )
                report = await verifier.run(task=task, diff=diff)
                reports.append(f"## Verifier: {verifier_type.title()}\n\n{report}")

        return "\n\n---\n\n".join(reports)

    async def _commit_changes(self, plan: Plan, task: Task) -> None:
        self.state = OrchestratorState.COMMITTING
        committer = self._create_agent(Committer)
        commit_message = await committer.run(task=task)

        if git.commit_changes(self.project_root, commit_message):
            display.success(f"Task '{task.id}' committed successfully.")

            # Delete the verification report file after successful commit
            report_file = self.report_dir / plan.plan_id / f"{task.id}.md"
            if report_file.exists():
                report_file.unlink()
        else:
            display.error(f"Failed to commit changes for task '{task.id}'.")
            display.warning(
                "Please fix the git commit issues manually and then retry the committer."
            )
            self.state = OrchestratorState.HALTED_FOR_ERROR
            raise Exception("Git commit failed. Manual intervention required.")

    def _select_next_task(self, plan: Plan) -> str:
        """Deterministically finds the next pending task whose dependencies are met."""
        display.info("Determining next task...")

        completed_task_ids = {
            task.id for task in plan.tasks if task.status == "completed"
        }

        for task in plan.tasks:
            if task.status == "pending" and all(
                dep_id in completed_task_ids for dep_id in task.dependencies
            ):
                display.info(f"Next task is '{task.id}'.")
                return task.id

        display.info("All tasks are complete.")
        return "PLAN_COMPLETE"

    def _get_latest_plan(self) -> Plan | None:
        """Finds the most recent plan file."""
        plan_dirs = sorted(self.plan_dir.iterdir(), key=os.path.getmtime, reverse=True)
        if not plan_dirs:
            return None

        latest_plan_path = plan_dirs[0] / "plan.yml"
        return filesystem.load_plan(latest_plan_path)

    def _select_plan_interactively(self) -> Plan | None:
        """Allows the user to choose from existing plans in .codeteam/planning."""
        plan_dirs = [d for d in self.plan_dir.iterdir() if d.is_dir()]
        if not plan_dirs:
            display.error(
                f"No plans found in {self.plan_dir.relative_to(self.project_root)}."
            )
            return None

        # Sort by creation time (newest first)
        plan_dirs = sorted(plan_dirs, key=os.path.getmtime, reverse=True)

        # Create menu options
        plan_options = []
        plan_map = {}

        for plan_dir in plan_dirs:
            plan_file = plan_dir / "plan.yml"
            if plan_file.exists():
                try:
                    plan = filesystem.load_plan(plan_file)
                    if plan:
                        option_name = f"{plan_dir.name}: {plan.description}"
                        plan_options.append(option_name)
                        plan_map[option_name] = plan
                except Exception:
                    # Skip invalid plans
                    continue

        if not plan_options:
            display.error(
                f"No valid plans found in {self.plan_dir.relative_to(self.project_root)}."
            )
            return None

        # Show interactive menu
        selected_option = interactive.get_menu_choice(
            "Select a plan to execute:", plan_options
        )

        return plan_map.get(selected_option)

    async def _get_user_decision(self) -> str:
        """Get user decision for verification review using interactive menus."""
        loop = asyncio.get_event_loop()

        def get_decision() -> str:
            choice = interactive.get_menu_choice(
                "Review the changes and choose an action:",
                ["/accept_changes", "/reject_changes"],
            )
            if choice == "/reject_changes":
                feedback = interactive.get_text_input(
                    "Provide feedback for rejection (optional)"
                )
                if feedback.strip():
                    return f"/reject_changes {feedback.strip()}"
                else:
                    return "/reject_changes"
            return choice

        return await loop.run_in_executor(None, get_decision)

    def display_dashboard(self) -> None:
        """Display a dashboard with project status overview."""
        # Get all plans
        plan_dirs = [d for d in self.plan_dir.iterdir() if d.is_dir()]
        if not plan_dirs:
            display.warning("No plans found in the project.")
            display.info("Run 'codeteam plan' to create a new plan.")
            return

        # Sort by creation time (newest first)
        plan_dirs = sorted(plan_dirs, key=os.path.getmtime, reverse=True)

        # Display all available plans
        plans_table = Table(title="Available Plans")
        plans_table.add_column("Plan ID", style="cyan", no_wrap=True)
        plans_table.add_column("Description", style="white")
        plans_table.add_column("Tasks", justify="center", style="yellow")
        plans_table.add_column("Status", style="bold")

        latest_plan = None
        for plan_dir in plan_dirs:
            plan_file = plan_dir / "plan.yml"
            if plan_file.exists():
                try:
                    plan = filesystem.load_plan(plan_file)
                    if plan:
                        if latest_plan is None:
                            latest_plan = plan

                        # Calculate plan status
                        total = len(plan.tasks)
                        completed = sum(
                            1 for t in plan.tasks if t.status == "completed"
                        )
                        failed = sum(1 for t in plan.tasks if t.status == "failed")

                        if failed > 0:
                            status = "[red]Has failures[/red]"
                        elif completed == total:
                            status = "[green]Complete[/green]"
                        elif completed > 0:
                            status = (
                                f"[yellow]In progress ({completed}/{total})[/yellow]"
                            )
                        else:
                            status = "[dim]Not started[/dim]"

                        plans_table.add_row(
                            plan.plan_id, plan.description, str(total), status
                        )
                except Exception:
                    # Skip invalid plans
                    continue

        display.print(plans_table)

        if not latest_plan:
            display.error("No valid plans found.")
            return

        # Display detailed view of the latest plan
        display.panel(
            f"Plan ID: {latest_plan.plan_id}\nDescription: {latest_plan.description}",
            title="Latest Plan Details",
        )

        # Create Task Progress table
        table = Table(title="Task Progress")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Dependencies", style="yellow")

        # Count tasks by status
        pending_count = 0
        completed_count = 0
        failed_count = 0

        for task in latest_plan.tasks:
            # Style status based on value
            status_style = "yellow"
            if task.status == "completed":
                status_style = "green"
                completed_count += 1
            elif task.status == "failed":
                status_style = "red"
                failed_count += 1
            else:
                pending_count += 1

            # Format dependencies
            deps_str = ", ".join(task.dependencies) if task.dependencies else "None"

            table.add_row(
                task.id,
                task.description,
                f"[{status_style}]{task.status}[/{status_style}]",
                deps_str,
            )

        display.print(table)

        # Display summary
        display.info(
            f"Total: {len(latest_plan.tasks)} tasks | "
            f"Completed: {completed_count} | "
            f"Pending: {pending_count} | "
            f"Failed: {failed_count}"
        )

        # Display Git Status
        git_status = git.get_git_status(self.project_root)
        if git_status and not git_status.startswith("Error"):
            display.panel(
                git_status if git_status else "Working tree clean", title="Git Status"
            )
        else:
            display.warning("Unable to get git status")

        # Suggest next steps
        display.panel(
            self._suggest_next_steps(latest_plan, pending_count, failed_count),
            title="Next Steps",
        )

    def _suggest_next_steps(
        self, plan: Plan, pending_count: int, failed_count: int
    ) -> str:
        """Suggest the next logical command based on current state."""
        suggestions = []

        if failed_count > 0:
            suggestions.append("- Review failed tasks and fix issues manually")
            suggestions.append("- Run 'codeteam code' to retry failed tasks")

        if pending_count > 0:
            # Check if there are tasks ready to execute
            completed_ids = {t.id for t in plan.tasks if t.status == "completed"}
            ready_tasks = [
                t
                for t in plan.tasks
                if t.status == "pending"
                and all(dep in completed_ids for dep in t.dependencies)
            ]

            if ready_tasks:
                suggestions.append(
                    f"- Run 'codeteam code' to execute {len(ready_tasks)} ready task(s)"
                )
            else:
                suggestions.append("- Some tasks have unmet dependencies")
                suggestions.append("- Review plan dependencies in plan.yml")

        if pending_count == 0 and failed_count == 0:
            suggestions.append("- All tasks completed!")
            suggestions.append("- Run 'codeteam plan' to create a new plan")

        return "\n".join(suggestions) if suggestions else "No specific recommendations"
