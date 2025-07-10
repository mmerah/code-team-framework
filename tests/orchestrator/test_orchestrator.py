"""Tests for the Orchestrator class, focusing on plan selection and progress tracking."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_team.models.plan import Plan, Task
from code_team.orchestrator.orchestrator import Orchestrator


@pytest.fixture
def temp_project_root() -> Generator[tuple[Path, Path], None, None]:
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_root = Path(tmp_dir)

        # Create necessary directories
        (project_root / ".codeteam" / "planning").mkdir(parents=True)
        (project_root / ".codeteam" / "reports").mkdir(parents=True)
        (project_root / ".codeteam" / "agent_instructions").mkdir(parents=True)

        # Create a basic config file
        config_path = project_root / ".codeteam" / "config.yml"
        config_path.write_text("""
llm:
  provider: "test"
  model: "test-model"
verification:
  commands: []
verifier_instances:
  arch: 0
  sec: 0
  perf: 0
  task: 0
""")

        yield project_root, config_path


@pytest.fixture
def orchestrator(temp_project_root: tuple[Path, Path]) -> Orchestrator:
    """Create an Orchestrator instance for testing."""
    project_root, config_path = temp_project_root

    with (
        patch("code_team.utils.llm.LLMProvider"),
        patch("code_team.utils.templates.TemplateManager"),
    ):
        return Orchestrator(project_root, config_path)


class TestPlanSelection:
    """Test plan selection functionality."""

    def test_select_plan_interactively_no_plans(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test behavior when no plans exist."""
        with patch("code_team.utils.ui.display.error") as mock_error:
            result = orchestrator._select_plan_interactively()
            assert result is None
            mock_error.assert_called_once_with("No plans found in .codeteam/planning.")

    def test_select_plan_interactively_with_plans(
        self, orchestrator: Orchestrator, temp_project_root: tuple[Path, Path]
    ) -> None:
        """Test plan selection when plans exist."""
        project_root, _ = temp_project_root

        # Create a test plan
        plan_dir = project_root / ".codeteam" / "planning" / "plan-0001"
        plan_dir.mkdir(parents=True)

        plan_content = """
plan_id: "test-plan"
description: "Test plan description"
tasks:
  - id: "task-001"
    description: "Test task"
    dependencies: []
"""
        (plan_dir / "plan.yml").write_text(plan_content)

        with (
            patch("code_team.utils.ui.interactive.get_menu_choice") as mock_choice,
            patch("code_team.utils.filesystem.load_plan") as mock_load,
        ):
            # Mock the plan loading
            mock_plan = Plan(
                plan_id="test-plan",
                description="Test plan description",
                tasks=[Task(id="task-001", description="Test task", dependencies=[])],
            )
            mock_load.return_value = mock_plan

            # Mock user selection
            mock_choice.return_value = "plan-0001: Test plan description"

            result = orchestrator._select_plan_interactively()

            assert result == mock_plan
            mock_choice.assert_called_once()

    def test_select_plan_interactively_invalid_plans(
        self, orchestrator: Orchestrator, temp_project_root: tuple[Path, Path]
    ) -> None:
        """Test behavior when plan files exist but are invalid."""
        project_root, _ = temp_project_root

        # Create an invalid plan
        plan_dir = project_root / ".codeteam" / "planning" / "plan-0001"
        plan_dir.mkdir(parents=True)
        (plan_dir / "plan.yml").write_text("invalid yaml content: [")

        with patch("code_team.utils.ui.display.error") as mock_error:
            result = orchestrator._select_plan_interactively()
            assert result is None
            mock_error.assert_called_once_with(
                "No valid plans found in .codeteam/planning."
            )


class TestReportManagement:
    """Test verification report management."""

    @pytest.mark.asyncio
    async def test_save_verification_report(
        self, orchestrator: Orchestrator, temp_project_root: tuple[Path, Path]
    ) -> None:
        """Test that verification reports are saved correctly."""
        project_root, _ = temp_project_root

        plan = Plan(
            plan_id="test-plan",
            description="Test plan",
            tasks=[Task(id="task-001", description="Test task", dependencies=[])],
        )
        task = plan.tasks[0]

        # Mock the verification process
        with (
            patch.object(orchestrator, "_run_verification") as mock_verify,
            patch.object(orchestrator, "_get_user_decision") as mock_decision,
            patch.object(orchestrator, "_create_agent") as mock_create_agent,
            patch.object(orchestrator, "_commit_changes"),
            patch("code_team.utils.filesystem.write_file") as mock_write,
            patch("code_team.utils.filesystem.read_file") as mock_read,
            patch("code_team.utils.filesystem.save_plan"),
            patch("code_team.utils.ui.display.panel"),
            patch("code_team.utils.ui.display.info"),
            patch("code_team.utils.ui.interactive.get_menu_choice") as mock_menu_choice,
            patch("rich.progress.Progress") as mock_progress,
        ):
            mock_verify.return_value = "Test verification report"
            mock_decision.return_value = "/accept_changes"  # Simulate accepting changes
            mock_menu_choice.return_value = "Proceed"  # Mock the menu choice
            mock_read.return_value = (
                "Mock prompt content"  # Mock reading the prompt file
            )

            # Mock the agents
            mock_prompter = AsyncMock()
            mock_prompter.run.return_value = Path(
                "/mock/path/task-001-prompt.md"
            )  # Prompter returns Path now
            mock_coder = AsyncMock()
            mock_coder.run.return_value = True  # Coder returns success

            def create_agent_side_effect(agent_class: type) -> Any:
                if agent_class.__name__ == "Prompter":
                    return mock_prompter
                elif agent_class.__name__ == "Coder":
                    return mock_coder
                return AsyncMock()

            mock_create_agent.side_effect = create_agent_side_effect

            mock_progress_instance = MagicMock()
            mock_progress.return_value = mock_progress_instance

            # Create a mock progress context
            with patch("code_team.orchestrator.orchestrator.Live"):
                # Create a mock TaskID
                mock_task_id = MagicMock()
                await orchestrator._execute_task_cycle(
                    plan, task, mock_progress_instance, mock_task_id
                )

            # Verify the report was saved
            expected_path = (
                project_root / ".codeteam" / "reports" / "test-plan" / "task-001.md"
            )
            mock_write.assert_called()

            # Check if write_file was called with the correct path and content
            write_calls = mock_write.call_args_list
            report_call = next(
                (
                    call
                    for call in write_calls
                    if call[0][0] == expected_path
                    and call[0][1] == "Test verification report"
                ),
                None,
            )
            assert report_call is not None

    @pytest.mark.asyncio
    async def test_delete_report_after_commit(
        self, orchestrator: Orchestrator, temp_project_root: tuple[Path, Path]
    ) -> None:
        """Test that verification reports are deleted after successful commit."""
        project_root, _ = temp_project_root

        plan = Plan(
            plan_id="test-plan",
            description="Test plan",
            tasks=[Task(id="task-001", description="Test task", dependencies=[])],
        )
        task = plan.tasks[0]

        # Create a mock report file
        report_dir = project_root / ".codeteam" / "reports" / "test-plan"
        report_dir.mkdir(parents=True)
        report_file = report_dir / "task-001.md"
        report_file.write_text("Test report content")

        with (
            patch.object(orchestrator, "_create_agent") as mock_create_agent,
            patch("code_team.utils.git.commit_changes") as mock_commit,
        ):
            # Mock successful commit
            mock_commit.return_value = True

            # Mock the committer agent
            mock_committer = AsyncMock()
            mock_committer.run.return_value = "Test commit message"
            mock_create_agent.return_value = mock_committer

            await orchestrator._commit_changes(plan, task)

            # Verify the report file was deleted
            assert not report_file.exists()


class TestProgressTracking:
    """Test progress tracking functionality."""

    @pytest.mark.asyncio
    async def test_single_progress_instance(
        self, orchestrator: Orchestrator, temp_project_root: tuple[Path, Path]
    ) -> None:
        """Test that run_code_phase uses a single Progress instance."""
        project_root, _ = temp_project_root

        # Create a test plan
        plan_dir = project_root / ".codeteam" / "planning" / "plan-0001"
        plan_dir.mkdir(parents=True)

        plan_content = """
plan_id: "test-plan"
description: "Test plan description"
tasks:
  - id: "task-001"
    description: "Test task"
    dependencies: []
    status: "pending"
"""
        (plan_dir / "plan.yml").write_text(plan_content)

        with (
            patch.object(orchestrator, "_select_plan_interactively") as mock_select,
            patch.object(orchestrator, "_execute_task_cycle") as mock_execute,
            patch.object(orchestrator, "_get_latest_plan") as mock_get_latest,
            patch(
                "code_team.orchestrator.orchestrator.Progress"
            ) as mock_progress_class,
            patch("code_team.orchestrator.orchestrator.Live") as mock_live,
        ):
            # Mock plan selection
            test_plan = Plan(
                plan_id="test-plan",
                description="Test plan description",
                tasks=[
                    Task(
                        id="task-001",
                        description="Test task",
                        dependencies=[],
                        status="pending",
                    )
                ],
            )
            mock_select.return_value = test_plan

            # Mock _get_latest_plan to return updated plan
            mock_get_latest.return_value = test_plan

            # Mock progress instance
            mock_progress = MagicMock()
            mock_progress_class.return_value = mock_progress

            # Mock execute_task_cycle to complete the task
            async def mock_task_cycle(
                plan: Plan, task: Task, progress: MagicMock, task_id: MagicMock
            ) -> None:
                task.status = "completed"

            mock_execute.side_effect = mock_task_cycle

            await orchestrator.run_code_phase()

            # Verify Progress was created once and used with Live
            mock_progress_class.assert_called_once()
            mock_live.assert_called_once_with(mock_progress, refresh_per_second=10)

            # Verify task was executed with the progress instance
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][2] == mock_progress  # progress parameter
