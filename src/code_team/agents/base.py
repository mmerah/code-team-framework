from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from code_team.models.config import CodeTeamConfig
from code_team.utils.llm import LLMProvider
from code_team.utils.templates import TemplateManager


class Agent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        template_manager: TemplateManager,
        config: CodeTeamConfig,
        project_root: Path,
    ):
        self.llm = llm_provider
        self.templates = template_manager
        self.config = config
        self.project_root = project_root

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """The main entry point for the agent's execution."""
        pass
