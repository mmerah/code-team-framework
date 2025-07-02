from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_code_sdk import (
    AssistantMessage,
    Message,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from code_team.models.config import CodeTeamConfig
from code_team.utils.llm import LLMProvider
from code_team.utils.templates import TemplateManager
from code_team.utils.ui import display


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

    @property
    def name(self) -> str:
        """Returns the agent's class name, e.g., 'Planner', 'Coder'."""
        return self.__class__.__name__

    async def _stream_and_collect_response(
        self, llm_stream: AsyncIterator[Message]
    ) -> str:
        """
        Streams agent activity to the console and collects the final text response.
        """
        full_response_parts: list[str] = []
        display.agent_thought(self.name, "is thinking...")

        async for message in llm_stream:
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        if text_content := block.text.strip():
                            # Use rich's markup escaping for user-generated content
                            escaped_text = text_content.replace("[", "[[").replace(
                                "]", "]]"
                            )
                            display.print(
                                f"  [grey50]Thought: {escaped_text[:150]}...[/grey50]"
                            )
                        full_response_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        display.print(
                            f"  [bold yellow]↳ Tool Use:[/bold yellow] [bold magenta]{block.name}[/bold magenta]"
                        )
                        for key, value in block.input.items():
                            escaped_value = (
                                str(value).replace("[", "[[").replace("]", "]]")
                            )
                            display.print(
                                f"    [green]{key}:[/green] {escaped_value[:200]}"
                            )
            elif isinstance(message, ResultMessage) and message.is_error:
                display.print(
                    f"  [bold red]Result: Error ({message.subtype})[/bold red]"
                )

        collected_response = "".join(full_response_parts).strip()
        display.agent_thought(self.name, "finished.")
        return collected_response

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """The main entry point for the agent's execution."""
        pass
