import asyncio
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
from rich.live import Live

from code_team.models.config import CodeTeamConfig
from code_team.utils.exceptions import ExceptionGroup
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
        self.retry_delay = 1.0

    @property
    def name(self) -> str:
        """Returns the agent's class name, e.g., 'Planner', 'Coder'."""
        return self.__class__.__name__

    def _get_model(self) -> str:
        """Get the model to use for this agent based on configuration."""
        # Convert class name to lowercase for config lookup
        # e.g., "Planner" -> "planner", "PlanVerifier" -> "plan_verifier"
        import re

        agent_name = self.__class__.__name__
        snake_case = re.sub("([A-Z]+)", r"_\1", agent_name).lower().lstrip("_")
        return self.config.llm.get_model_for_agent(snake_case)

    async def _stream_and_collect_response(
        self, llm_stream: AsyncIterator[Message]
    ) -> str:
        """
        Streams agent activity to the console and collects the final text response.
        """
        full_response_parts: list[str] = []
        accumulated_content: list[str] = []

        # Create initial panel with "thinking..." message
        panel = display.create_agent_panel(self.name, "Thinking...")

        with Live(
            panel, console=display.console, refresh_per_second=4, transient=False
        ) as live:
            try:
                async for message in llm_stream:
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                full_response_parts.append(block.text)
                                if text_content := block.text.strip():
                                    # Use rich's markup escaping for user-generated content
                                    escaped_text = text_content.replace(
                                        "[", "[["
                                    ).replace("]", "]]")
                                    accumulated_content.append(escaped_text)
                                    # Update the panel with scrollable content
                                    panel = display.create_scrollable_panel(
                                        self.name, accumulated_content
                                    )
                                    live.update(panel)
                            elif isinstance(block, ToolUseBlock):
                                tool_text = f"[bold yellow]↳ Tool Use:[/bold yellow] [bold magenta]{block.name}[/bold magenta]"
                                accumulated_content.append(tool_text)
                                for key, value in block.input.items():
                                    escaped_value = (
                                        str(value).replace("[", "[[").replace("]", "]]")
                                    )
                                    accumulated_content.append(
                                        f"  [green]{key}:[/green] {escaped_value[:200]}"
                                    )
                                # Update panel with scrollable content
                                panel = display.create_scrollable_panel(
                                    self.name, accumulated_content
                                )
                                live.update(panel)
                    elif isinstance(message, ResultMessage) and message.is_error:
                        error_text = (
                            f"[bold red]Result: Error ({message.subtype})[/bold red]"
                        )
                        accumulated_content.append(error_text)
                        panel = display.create_scrollable_panel(
                            self.name, accumulated_content
                        )
                        live.update(panel)
            except ExceptionGroup as eg:
                display.warning(
                    "Stream interrupted due to SDK error. Partial response collected."
                )
                for exc in eg.exceptions:
                    if hasattr(exc, "args") and exc.args:
                        display.warning(f"  Error: {exc.args[0]}")
                raise
            except Exception as e:
                display.warning(f"Stream interrupted: {e}. Partial response collected.")
                raise

        collected_response = "".join(full_response_parts).strip()
        return collected_response

    async def _robust_llm_query(
        self, prompt: str, system_prompt: str, allowed_tools: list[str] | None = None
    ) -> str:
        """
        Performs an LLM query with robust error handling for TaskGroup and JSON errors.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    display.info(
                        f"Retrying request (attempt {attempt + 1}/{max_retries})..."
                    )

                llm_stream = self.llm.query(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    allowed_tools=allowed_tools,
                    model=self._get_model(),
                )
                return await self._stream_and_collect_response(llm_stream)
            except ExceptionGroup:
                display.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed with TaskGroup error"
                )
                if attempt == max_retries - 1:
                    display.error("All retry attempts failed due to SDK issues.")
                    return self._get_fallback_response(prompt)
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                display.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    display.error("All retry attempts failed.")
                    return self._get_fallback_response(prompt)
                await asyncio.sleep(self.retry_delay)

        return self._get_fallback_response(prompt)

    async def _render_and_query(
        self, template_name: str, prompt: str, **kwargs: Any
    ) -> str:
        """
        Convenience method to render a template and query the LLM.

        Args:
            template_name: Name of the template file to render
            prompt: The user prompt to send to the LLM
            **kwargs: Template variables for rendering

        Returns:
            The LLM response
        """
        system_prompt = self.templates.render(template_name, **kwargs)
        return await self._robust_llm_query(prompt, system_prompt)

    def _get_fallback_response(self, prompt: str) -> str:
        """
        Provides a contextual fallback response when LLM queries fail.
        """
        if "clarifying questions" in prompt.lower():
            return "I'd be happy to help create a plan. Could you provide more details about what you'd like to accomplish? What are the main goals and requirements for this project?"
        elif "plan.yml" in prompt:
            return "I encountered a technical issue while generating the plan files. Please try running the planner again, or consider creating a basic plan structure manually."
        else:
            return "I apologize, but I encountered a technical issue with the AI service. Please try your request again. If the problem persists, there may be an issue with the underlying AI service connection."

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """The main entry point for the agent's execution."""
        pass
