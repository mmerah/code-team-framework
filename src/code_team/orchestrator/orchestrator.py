import asyncio
import os
import subprocess
from pathlib import Path

import yaml

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
        self.plan_dir = self.project_root / "docs" / "planning"
        self.log_dir = self.project_root / ".codeteam" / "logs"
        self.report_dir = self.project_root / ".codeteam" / "reports"

        self.llm_provider = llm.LLMProvider(self.config.llm, str(project_root))
        self.template_manager = templates.TemplateManager(
            project_root / "config" / "agent_instructions"
        )

        self._ensure_dirs_exist()

    def _load_config(self, path: Path) -> CodeTeamConfig:
        content = filesystem.read_file(path)
        if not content:
            raise FileNotFoundError("Config file not found.")
        return CodeTeamConfig.model_validate(yaml.safe_load(content))

    def _ensure_dirs_exist(self) -> None:
        self.plan_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    async def run_plan_phase(self, initial_request: str) -> None:
        """Runs the planning phase of the workflow."""
        self.state = OrchestratorState.PLANNING_DRAFTING
        planner = Planner(
            self.llm_provider, self.template_manager, self.config, self.project_root
        )
        plan_files = await planner.run(initial_request)

        if not plan_files:
            self.state = OrchestratorState.HALTED_FOR_ERROR
            display.error("Failed to generate plan files.")
            return

        plan_id = f"plan-{len(list(self.plan_dir.iterdir())) + 1:04d}"
        current_plan_dir = self.plan_dir / plan_id
        current_plan_dir.mkdir()

        filesystem.write_file(current_plan_dir / "plan.yml", plan_files["plan.yml"])
        filesystem.write_file(
            current_plan_dir / "ACCEPTANCE_CRITERIA.md",
            plan_files["ACCEPTANCE_CRITERIA.md"],
        )

        self.state = OrchestratorState.PLANNING_AWAITING_REVIEW
        display.success(f"Plan '{plan_id}' created in {current_plan_dir}")
        # Simple interactive loop for plan review
        while self.state == OrchestratorState.PLANNING_AWAITING_REVIEW:
            user_input = interactive.get_menu_choice(
                "Review the plan and choose an action:",
                ["/verify_plan", "/accept_plan"],
            )
            if user_input == "/verify_plan":
                await self._verify_plan(current_plan_dir)
            elif user_input == "/accept_plan":
                display.success("Plan accepted. You can now run the coding phase.")
                break

    async def _verify_plan(self, plan_dir: Path) -> None:
        self.state = OrchestratorState.PLANNING_VERIFYING
        verifier = PlanVerifier(
            self.llm_provider, self.template_manager, self.config, self.project_root
        )

        plan_content = filesystem.read_file(plan_dir / "plan.yml") or ""
        criteria_content = (
            filesystem.read_file(plan_dir / "ACCEPTANCE_CRITERIA.md") or ""
        )

        feedback = await verifier.run(plan_content, criteria_content)
        filesystem.write_file(plan_dir / "FEEDBACK.md", feedback)

        display.panel(feedback, title="Plan Verification Feedback")

        self.state = OrchestratorState.PLANNING_AWAITING_REVIEW
        display.info("You can now revise the plan manually or '/accept_plan'.")

    async def run_code_phase(self) -> None:
        """Runs the main coding and verification loop."""
        plan = self._get_latest_plan()
        if not plan:
            display.error("No active plan found. Please run the planning phase first.")
            return

        # Count pending tasks for progress tracking
        pending_tasks = [t for t in plan.tasks if t.status == "pending"]
        total_tasks = len(pending_tasks)

        if total_tasks == 0:
            display.success("🎉 All tasks are already completed!")
            return

        # Create overall progress bar
        overall_progress = display.create_overall_progress()

        with overall_progress:
            overall_task = overall_progress.add_task(
                f"[progress]Executing {total_tasks} tasks...[/progress]",
                total=total_tasks,
            )

            self.state = OrchestratorState.CODING_AWAITING_TASK_SELECTION
            while self.state not in [
                OrchestratorState.PLAN_COMPLETE,
                OrchestratorState.HALTED_FOR_ERROR,
            ]:
                task_id = self._select_next_task(plan)
                if task_id == "PLAN_COMPLETE":
                    self.state = OrchestratorState.PLAN_COMPLETE
                    overall_progress.update(overall_task, completed=total_tasks)
                    display.success("🎉 Plan complete! All tasks have been finished.")
                    break

                task = next((t for t in plan.tasks if t.id == task_id), None)
                if not task:
                    self.state = OrchestratorState.HALTED_FOR_ERROR
                    display.error(f"Task '{task_id}' not found in plan.")
                    break

                await self._execute_task_cycle(plan, task)

                # Update progress
                completed_count = len(
                    [t for t in plan.tasks if t.status == "completed"]
                )
                overall_progress.update(overall_task, completed=completed_count)

                # Reload plan to get updated task statuses
                plan = self._get_latest_plan()
                if not plan:
                    break

    async def _execute_task_cycle(self, plan: Plan, task: Task) -> None:
        """Handles the full lifecycle for a single task, allowing for retries."""
        verification_feedback: str | None = None
        max_retries = 3
        current_try = 0

        while current_try < max_retries:
            current_try += 1

            # Create task-level progress indicator
            task_progress = display.create_task_progress()

            with task_progress:
                # CODING
                self.state = OrchestratorState.CODING_PROMPTING
                prompting_task = task_progress.add_task(
                    f"[progress]Preparing prompt for task {task.id}...[/progress]"
                )

                prompter = Prompter(
                    self.llm_provider,
                    self.template_manager,
                    self.config,
                    self.project_root,
                )
                coder_prompt = await prompter.run(task)
                task_progress.update(prompting_task, completed=1)

                self.state = OrchestratorState.CODING_IN_PROGRESS
                coding_task = task_progress.add_task(
                    f"[progress]Coder working on task {task.id}...[/progress]"
                )

                coder = Coder(
                    self.llm_provider,
                    self.template_manager,
                    self.config,
                    self.project_root,
                )
                # Pass the feedback from the previous loop iteration (if any)
                await coder.run(
                    coder_prompt, verification_feedback=verification_feedback
                )
                task_progress.update(coding_task, completed=1)

                # VERIFICATION
                self.state = OrchestratorState.VERIFYING
                verify_task = task_progress.add_task(
                    f"[progress]Verifying changes for task {task.id}...[/progress]"
                )

                verification_report = await self._run_verification(task)
                task_progress.update(verify_task, completed=1)

            self.state = OrchestratorState.AWAITING_VERIFICATION_REVIEW
            display.panel(verification_report, title="Verification Report")

            user_decision = await self._get_user_decision()

            if user_decision.lower().startswith("/accept_changes"):
                await self._commit_changes(task)
                task.status = "completed"
                filesystem.save_plan(self.plan_dir / plan.plan_id / "plan.yml", plan)
                return  # Exit the loop and task cycle successfully

            elif user_decision.lower().startswith("/reject_changes"):
                feedback_text = user_decision.replace("/reject_changes", "").strip()
                verification_feedback = (
                    f"--- Previous Verification Report ---\n{verification_report}\n\n"
                    f"--- User Feedback for This Attempt ---\n{feedback_text}"
                )
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

    async def _commit_changes(self, task: Task) -> None:
        self.state = OrchestratorState.COMMITTING
        committer = Committer(
            self.llm_provider, self.template_manager, self.config, self.project_root
        )
        commit_message = await committer.run(task)

        if git.commit_changes(self.project_root, commit_message):
            display.success(f"Task '{task.id}' committed successfully.")
        else:
            display.error(f"Failed to commit changes for task '{task.id}'.")

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
