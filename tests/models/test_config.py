"""Unit tests for configuration models."""

import pytest
from pydantic import ValidationError

from code_team.models.config import (
    CodeTeamConfig,
    LLMConfig,
    PathConfig,
    TemplateConfig,
    VerificationCommand,
    VerificationConfig,
    VerificationMetrics,
    VerifierInstances,
)


class TestLLMConfig:
    """Test the LLMConfig model."""

    def test_default_agent_models(self) -> None:
        """Test that LLMConfig has correct default models for all agents."""
        config = LLMConfig()
        assert config.planner == "sonnet"
        assert config.coder == "sonnet"
        assert config.prompter == "sonnet"
        assert config.plan_verifier == "sonnet"
        assert config.verifier_arch == "sonnet"
        assert config.verifier_task == "sonnet"
        assert config.verifier_sec == "sonnet"
        assert config.verifier_perf == "sonnet"
        assert config.commit_agent == "sonnet"

    def test_custom_agent_models(self) -> None:
        """Test that LLMConfig accepts custom models for agents."""
        config = LLMConfig(
            planner="opus",
            coder="haiku",
            verifier_arch="sonnet",
        )
        assert config.planner == "opus"
        assert config.coder == "haiku"
        assert config.verifier_arch == "sonnet"
        # Others should still be defaults
        assert config.prompter == "sonnet"
        assert config.plan_verifier == "sonnet"

    def test_get_model_for_agent(self) -> None:
        """Test the get_model_for_agent method."""
        config = LLMConfig(planner="opus", coder="haiku")

        # Test agents with custom models
        assert config.get_model_for_agent("planner") == "opus"
        assert config.get_model_for_agent("coder") == "haiku"

        # Test agents with default models
        assert config.get_model_for_agent("prompter") == "sonnet"

        # Test case insensitive
        assert config.get_model_for_agent("PLANNER") == "opus"


class TestVerificationCommand:
    """Test the VerificationCommand model."""

    def test_create_verification_command(self) -> None:
        """Test creating a VerificationCommand."""
        cmd = VerificationCommand(name="pytest", command="pytest tests/")
        assert cmd.name == "pytest"
        assert cmd.command == "pytest tests/"

    def test_verification_command_requires_fields(self) -> None:
        """Test that VerificationCommand requires all fields."""
        with pytest.raises(ValidationError):
            VerificationCommand(**{"name": "pytest"})
        with pytest.raises(ValidationError):
            VerificationCommand(**{"command": "pytest tests/"})


class TestVerificationMetrics:
    """Test the VerificationMetrics model."""

    def test_default_metrics(self) -> None:
        """Test that VerificationMetrics has correct defaults."""
        metrics = VerificationMetrics()
        assert metrics.max_file_lines == 500
        assert metrics.max_method_lines == 80

    def test_custom_metrics(self) -> None:
        """Test that VerificationMetrics accepts custom values."""
        metrics = VerificationMetrics(max_file_lines=1000, max_method_lines=100)
        assert metrics.max_file_lines == 1000
        assert metrics.max_method_lines == 100


class TestVerificationConfig:
    """Test the VerificationConfig model."""

    def test_default_verification_config(self) -> None:
        """Test that VerificationConfig has correct defaults."""
        config = VerificationConfig()
        assert config.commands == []
        assert isinstance(config.metrics, VerificationMetrics)

    def test_custom_verification_config(self) -> None:
        """Test that VerificationConfig accepts custom values."""
        cmd = VerificationCommand(name="test", command="make test")
        metrics = VerificationMetrics(max_file_lines=600)
        config = VerificationConfig(commands=[cmd], metrics=metrics)
        assert len(config.commands) == 1
        assert config.commands[0].name == "test"
        assert config.metrics.max_file_lines == 600


class TestVerifierInstances:
    """Test the VerifierInstances model."""

    def test_default_instances(self) -> None:
        """Test that VerifierInstances has correct defaults."""
        instances = VerifierInstances()
        assert instances.architecture == 1
        assert instances.task_completion == 1
        assert instances.security == 0
        assert instances.performance == 0

    def test_custom_instances(self) -> None:
        """Test that VerifierInstances accepts custom values."""
        instances = VerifierInstances(
            architecture=2, task_completion=3, security=1, performance=1
        )
        assert instances.architecture == 2
        assert instances.task_completion == 3
        assert instances.security == 1
        assert instances.performance == 1


class TestPathConfig:
    """Test the PathConfig model."""

    def test_default_paths(self) -> None:
        """Test that PathConfig has correct defaults."""
        config = PathConfig()
        assert config.plan_dir == ".codeteam/planning"
        assert config.report_dir == ".codeteam/reports"
        assert config.config_dir == ".codeteam"
        assert config.agent_instructions_dir == ".codeteam/agent_instructions"

    def test_custom_paths(self) -> None:
        """Test that PathConfig accepts custom values."""
        config = PathConfig(
            plan_dir="custom/plans",
            report_dir="custom/reports",
            config_dir="custom/config",
            agent_instructions_dir="custom/config/instructions",
        )
        assert config.plan_dir == "custom/plans"
        assert config.report_dir == "custom/reports"
        assert config.config_dir == "custom/config"
        assert config.agent_instructions_dir == "custom/config/instructions"


class TestCodeTeamConfig:
    """Test the CodeTeamConfig model."""

    def test_default_config(self) -> None:
        """Test that CodeTeamConfig has correct defaults."""
        config = CodeTeamConfig()
        assert config.version == 1.0
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.verification, VerificationConfig)
        assert isinstance(config.verifier_instances, VerifierInstances)
        assert isinstance(config.paths, PathConfig)
        assert isinstance(config.templates, TemplateConfig)

    def test_custom_config(self) -> None:
        """Test that CodeTeamConfig accepts custom values."""
        llm = LLMConfig(planner="opus", coder="haiku")
        verification = VerificationConfig(
            commands=[VerificationCommand(name="test", command="pytest")]
        )
        verifier_instances = VerifierInstances(security=1)
        paths = PathConfig(plan_dir="custom/plans")

        config = CodeTeamConfig(
            version=2.0,
            llm=llm,
            verification=verification,
            verifier_instances=verifier_instances,
            paths=paths,
        )

        assert config.version == 2.0
        assert config.llm.planner == "opus"
        assert config.llm.coder == "haiku"
        assert len(config.verification.commands) == 1
        assert config.verifier_instances.security == 1
        assert config.paths.plan_dir == "custom/plans"


class TestTemplateConfig:
    """Test the TemplateConfig model."""

    def test_default_template_config(self) -> None:
        """Test that TemplateConfig has correct defaults."""
        config = TemplateConfig()
        assert config.guideline_files == [
            "ARCHITECTURE_GUIDELINES.md",
            "CODING_GUIDELINES.md",
            "AGENT_OBJECTIVITY.md",
        ]
        assert config.exclude_dirs == [
            ".git",
            ".mypy_cache",
            ".ruff_cache",
            ".venv",
            ".idea",
            "__pycache__",
            ".codeteam",
            "node_modules",
            "build",
        ]

    def test_custom_template_config(self) -> None:
        """Test that TemplateConfig accepts custom values."""
        config = TemplateConfig(
            guideline_files=["CUSTOM_GUIDELINES.md"],
            exclude_dirs=["custom_exclude", "another_exclude"],
        )
        assert config.guideline_files == ["CUSTOM_GUIDELINES.md"]
        assert config.exclude_dirs == ["custom_exclude", "another_exclude"]

    def test_empty_exclude_dirs(self) -> None:
        """Test that TemplateConfig accepts empty exclude_dirs list."""
        config = TemplateConfig(exclude_dirs=[])
        assert config.exclude_dirs == []

    def test_partial_custom_config(self) -> None:
        """Test that TemplateConfig allows partial customization."""
        config = TemplateConfig(exclude_dirs=["only_this"])
        # guideline_files should still be default
        assert config.guideline_files == [
            "ARCHITECTURE_GUIDELINES.md",
            "CODING_GUIDELINES.md",
            "AGENT_OBJECTIVITY.md",
        ]
        # exclude_dirs should be custom
        assert config.exclude_dirs == ["only_this"]
