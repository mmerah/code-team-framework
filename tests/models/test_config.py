"""Unit tests for configuration models."""

import pytest
from pydantic import ValidationError

from code_team.models.config import (
    AgentConfig,
    CoderAgentConfig,
    CodeTeamConfig,
    LLMConfig,
    VerificationCommand,
    VerificationConfig,
    VerificationMetrics,
    VerifierInstances,
)


class TestLLMConfig:
    """Test the LLMConfig model."""

    def test_default_model(self) -> None:
        """Test that LLMConfig has correct default model."""
        config = LLMConfig()
        assert config.model == "sonnet"

    def test_custom_model(self) -> None:
        """Test that LLMConfig accepts custom model."""
        config = LLMConfig(model="opus")
        assert config.model == "opus"


class TestCoderAgentConfig:
    """Test the CoderAgentConfig model."""

    def test_default_log_summarize_threshold(self) -> None:
        """Test default log summarize threshold."""
        config = CoderAgentConfig()
        assert config.log_summarize_threshold == 75000

    def test_custom_log_summarize_threshold(self) -> None:
        """Test custom log summarize threshold."""
        config = CoderAgentConfig(log_summarize_threshold=100000)
        assert config.log_summarize_threshold == 100000


class TestAgentConfig:
    """Test the AgentConfig model."""

    def test_default_coder_config(self) -> None:
        """Test default CoderAgentConfig."""
        config = AgentConfig()
        assert isinstance(config.coder, CoderAgentConfig)
        assert config.coder.log_summarize_threshold == 75000

    def test_custom_coder_config(self) -> None:
        """Test custom CoderAgentConfig."""
        coder_config = CoderAgentConfig(log_summarize_threshold=50000)
        config = AgentConfig(coder=coder_config)
        assert config.coder.log_summarize_threshold == 50000


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


class TestCodeTeamConfig:
    """Test the CodeTeamConfig model."""

    def test_default_config(self) -> None:
        """Test that CodeTeamConfig has correct defaults."""
        config = CodeTeamConfig()
        assert config.version == 1.0
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.agents, AgentConfig)
        assert isinstance(config.verification, VerificationConfig)
        assert isinstance(config.verifier_instances, VerifierInstances)

    def test_custom_config(self) -> None:
        """Test that CodeTeamConfig accepts custom values."""
        llm = LLMConfig(model="opus")
        agents = AgentConfig(coder=CoderAgentConfig(log_summarize_threshold=50000))
        verification = VerificationConfig(
            commands=[VerificationCommand(name="test", command="pytest")]
        )
        verifier_instances = VerifierInstances(security=1)

        config = CodeTeamConfig(
            version=2.0,
            llm=llm,
            agents=agents,
            verification=verification,
            verifier_instances=verifier_instances,
        )

        assert config.version == 2.0
        assert config.llm.model == "opus"
        assert config.agents.coder.log_summarize_threshold == 50000
        assert len(config.verification.commands) == 1
        assert config.verifier_instances.security == 1
