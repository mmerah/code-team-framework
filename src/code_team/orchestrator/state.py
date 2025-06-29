from enum import Enum, auto


class OrchestratorState(Enum):
    """Defines the possible states of the orchestrator."""

    IDLE = auto()
    PLANNING_DRAFTING = auto()
    PLANNING_AWAITING_REVIEW = auto()
    PLANNING_VERIFYING = auto()
    CODING_AWAITING_TASK_SELECTION = auto()
    CODING_PROMPTING = auto()
    CODING_IN_PROGRESS = auto()
    VERIFYING = auto()
    AWAITING_VERIFICATION_REVIEW = auto()
    COMMITTING = auto()
    PLAN_COMPLETE = auto()
    HALTED_FOR_ERROR = auto()
