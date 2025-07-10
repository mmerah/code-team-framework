from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for Large Language Models.

    Each agent has its own explicit model configuration.
    """

    # Per-agent model configuration (all explicit with defaults)
    planner: str = "sonnet"
    coder: str = "sonnet"
    prompter: str = "sonnet"
    plan_verifier: str = "sonnet"
    verifier_arch: str = "sonnet"
    verifier_task: str = "sonnet"
    verifier_sec: str = "sonnet"
    verifier_perf: str = "sonnet"
    commit_agent: str = "sonnet"

    def get_model_for_agent(self, agent_name: str) -> str:
        """Get the model to use for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., 'planner', 'coder', etc.)

        Returns:
            The model name to use for this agent
        """
        # Return the agent's configured model directly
        model: str = getattr(self, agent_name.lower())
        return model


class VerificationCommand(BaseModel):
    name: str
    command: str


class VerificationMetrics(BaseModel):
    max_file_lines: int = 500
    max_method_lines: int = 80


class VerificationConfig(BaseModel):
    commands: list[VerificationCommand] = Field(
        default_factory=list[VerificationCommand]
    )
    metrics: VerificationMetrics = Field(default_factory=VerificationMetrics)


class VerifierInstances(BaseModel):
    architecture: int = 1
    task_completion: int = 1
    security: int = 0
    performance: int = 0


class PathConfig(BaseModel):
    """Configuration for file system paths used by the framework."""

    plan_dir: str = ".codeteam/planning"
    report_dir: str = ".codeteam/reports"
    config_dir: str = ".codeteam"
    agent_instructions_dir: str = ".codeteam/agent_instructions"
    template_dir: str = ".codeteam/agent_instructions"


class TemplateConfig(BaseModel):
    """Configuration for template rendering and guideline files."""

    guideline_files: list[str] = Field(
        default_factory=lambda: [
            "ARCHITECTURE_GUIDELINES.md",
            "CODING_GUIDELINES.md",
            "AGENT_OBJECTIVITY.md",
        ]
    )
    exclude_dirs: list[str] = Field(
        default_factory=lambda: [
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
    )


class CodeTeamConfig(BaseModel):
    version: float = 1.0
    llm: LLMConfig = Field(default_factory=LLMConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    verifier_instances: VerifierInstances = Field(default_factory=VerifierInstances)
    paths: PathConfig = Field(default_factory=PathConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
