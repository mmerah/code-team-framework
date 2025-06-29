import asyncio
import os
from pathlib import Path

import yaml

from code_team.agents.coder import Coder
from code_team.agents.committer import Committer
from code_team.agents.plan_verifier import PlanVerifier
from code_team.agents.planner import Planner
from code_team.agents.prompter import Prompter
from code_team.agents.situation_evaluator import SituationEvaluator
from code_team.agents.verifiers import CodeVerifier
from code_team.models.config import CodeTeamConfig
from code_team.models.plan import Plan, Task
from code_team.orchestrator.state import OrchestratorState
from code_team.utils import filesystem, git, llm, templates


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
            print("Failed to generate plan files.")
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
        print(f"\nPlan '{plan_id}' created in {current_plan_dir}")
        print(
            "Review the plan. To verify it, type '/verify_plan'. To accept, type '/accept_plan'."
        )

        # Simple interactive loop for plan review
        while self.state == OrchestratorState.PLANNING_AWAITING_REVIEW:
            user_input = input("> ").strip()
            if user_input == "/verify_plan":
                await self._verify_plan(current_plan_dir)
            elif user_input == "/accept_plan":
                print("Plan accepted. You can now run the coding phase.")
                break
            else:
                print("Invalid command.")

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

        print("\n--- Plan Verification Feedback ---")
        print(feedback)
        print("---------------------------------")

        self.state = OrchestratorState.PLANNING_AWAITING_REVIEW
        print("You can now revise the plan manually or '/accept_plan'.")

    async def run_code_phase(self) -> None:
        """Runs the main coding and verification loop."""
        plan = self._get_latest_plan()
        if not plan:
            print("No active plan found. Please run the planning phase first.")
            return

        self.state = OrchestratorState.CODING_AWAITING_TASK_SELECTION
        while self.state not in [
            OrchestratorState.PLAN_COMPLETE,
            OrchestratorState.HALTED_FOR_ERROR,
        ]:
            task_id = await self._select_next_task(plan)
            if task_id == "PLAN_COMPLETE":
                self.state = OrchestratorState.PLAN_COMPLETE
                print("\n🎉 Plan complete! All tasks have been finished.")
                break

            task = next((t for t in plan.tasks if t.id == task_id), None)
            if not task:
                self.state = OrchestratorState.HALTED_FOR_ERROR
                print(f"Error: Task '{task_id}' not found in plan.")
                break

            await self._execute_task_cycle(plan, task)
            # Reload plan to get updated task statuses
            plan = self._get_latest_plan()
            if not plan:
                break

    async def _execute_task_cycle(self, plan: Plan, task: Task) -> None:
        """Handles the full lifecycle for a single task."""
        # CODING
        self.state = OrchestratorState.CODING_PROMPTING
        prompter = Prompter(
            self.llm_provider, self.template_manager, self.config, self.project_root
        )
        coder_prompt = await prompter.run(task)

        self.state = OrchestratorState.CODING_IN_PROGRESS
        coder = Coder(
            self.llm_provider, self.template_manager, self.config, self.project_root
        )
        await coder.run(coder_prompt)

        # VERIFICATION
        self.state = OrchestratorState.VERIFYING
        verification_report = await self._run_verification(task)

        self.state = OrchestratorState.AWAITING_VERIFICATION_REVIEW
        print("\n--- Verification Report ---")
        print(verification_report)
        print("---------------------------")
        print(
            "Review the changes. Type '/accept_changes' or '/reject_changes [your feedback]'."
        )

        user_decision = await self._get_user_decision()

        if user_decision.startswith("/accept_changes"):
            await self._commit_changes(task)
            task.status = "completed"
        else:
            # Rerunning the coder with feedback would go here. For now, we just mark as failed.
            print(
                "Changes rejected. Marking task as failed. Manual intervention needed."
            )
            task.status = "failed"

        filesystem.save_plan(self.plan_dir / plan.plan_id / "plan.yml", plan)

    async def _run_verification(self, task: Task) -> str:
        """Runs all configured verification steps."""
        diff = git.get_git_diff(self.project_root)
        reports: list[str] = []

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
            print(f"Task '{task.id}' committed successfully.")
        else:
            print(f"Failed to commit changes for task '{task.id}'.")

    async def _select_next_task(self, plan: Plan) -> str:
        evaluator = SituationEvaluator(
            self.llm_provider, self.template_manager, self.config, self.project_root
        )
        return await evaluator.run(plan)

    def _get_latest_plan(self) -> Plan | None:
        """Finds the most recent plan file."""
        plan_dirs = sorted(self.plan_dir.iterdir(), key=os.path.getmtime, reverse=True)
        if not plan_dirs:
            return None

        latest_plan_path = plan_dirs[0] / "plan.yml"
        return filesystem.load_plan(latest_plan_path)

    async def _get_user_decision(self) -> str:
        """Simple async wrapper for input to allow for future UI integration."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "> ")
