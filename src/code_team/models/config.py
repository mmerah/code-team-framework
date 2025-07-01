from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    model: str = "sonnet"


class CoderAgentConfig(BaseModel):
    log_summarize_threshold: int = 75000


class AgentConfig(BaseModel):
    coder: CoderAgentConfig = Field(default_factory=CoderAgentConfig)


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


class CodeTeamConfig(BaseModel):
    version: float = 1.0
    llm: LLMConfig = Field(default_factory=LLMConfig)
    agents: AgentConfig = Field(default_factory=AgentConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    verifier_instances: VerifierInstances = Field(default_factory=VerifierInstances)
