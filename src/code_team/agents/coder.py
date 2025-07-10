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

from code_team.agents.base import Agent
from code_team.models.config import CodeTeamConfig
from code_team.utils import filesystem
from code_team.utils.exceptions import ExceptionGroup
from code_team.utils.llm import LLMProvider
from code_team.utils.templates import TemplateManager
from code_team.utils.ui import display


class Coder(Agent):
    """Executes a detailed prompt to modify the codebase."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        template_manager: TemplateManager,
        config: CodeTeamConfig,
        project_root: Path,
    ) -> None:
        """Initialize the Coder agent."""
        super().__init__(llm_provider, template_manager, config, project_root)
        self._live_display: Live | None = None
        self._current_tool_info: list[str] = []

    async def run(self, **kwargs: Any) -> bool:
        """
        Runs the Coder agent to perform code modifications.

        Args:
            **kwargs: Keyword arguments containing:
                - coder_prompt: Path to the file containing detailed instructions from the Prompter.
                - verification_feedback: Optional feedback from a previous failed run.
                - plan_id: The ID of the current plan being executed (optional).

        Returns:
            True if the process completed, False otherwise.
        """
        coder_prompt_path: Path = kwargs["coder_prompt"]
        verification_feedback: str | None = kwargs.get("verification_feedback")
        plan_id: str | None = kwargs.get("plan_id")

        # Read the prompt from the file
        coder_prompt = filesystem.read_file(coder_prompt_path)
        if not coder_prompt:
            display.error(f"Failed to read coder prompt from {coder_prompt_path}")
            return False

        system_prompt = self.templates.render(
            "CODER_INSTRUCTIONS.md",
            VERIFICATION_FEEDBACK=verification_feedback
            or "No feedback from previous run.",
            PLAN_ID=plan_id or "unknown",
        )

        prompt = (
            "Here are your instructions. Follow them carefully and log your actions."
        )

        allowed_tools = ["Read", "Write", "Bash"]

        # Create a Live display for real-time tool usage updates
        with display.create_live_display() as live:
            self._live_display = live
            self._current_tool_info = []

            try:
                await self._robust_coder_query(
                    prompt=prompt,
                    system_prompt=coder_prompt + "\n\n" + system_prompt,
                    allowed_tools=allowed_tools,
                )
            except Exception as e:
                display.error(f"Coder encountered an error: {e}")
                return False
            finally:
                # Clear the live display reference
                self._live_display = None
                self._current_tool_info = []

        return True

    async def _robust_coder_query(
        self, prompt: str, system_prompt: str, allowed_tools: list[str] | None = None
    ) -> None:
        """
        Performs a robust LLM query with custom message handling for the Coder.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    display.info(
                        f"Retrying coder request (attempt {attempt + 1}/{max_retries})..."
                    )

                llm_stream = self.llm.query(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    allowed_tools=allowed_tools,
                    model=self._get_model(),
                )

                # Custom streaming for Coder since it needs to handle ResultMessage differently
                async for message in llm_stream:
                    await self._handle_coder_message(message)

                return

            except ExceptionGroup:
                display.warning(
                    f"Coder attempt {attempt + 1}/{max_retries} failed with TaskGroup error"
                )
                if attempt == max_retries - 1:
                    display.error("All coder retry attempts failed due to SDK issues.")
                    raise
                import asyncio

                await asyncio.sleep(1)
            except Exception as e:
                display.warning(
                    f"Coder attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt == max_retries - 1:
                    display.error("All coder retry attempts failed.")
                    raise
                import asyncio

                await asyncio.sleep(1)

    async def _handle_coder_message(self, message: Message) -> None:
        """Handle individual messages from the Coder's LLM stream."""
        # Using the global display manager

        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    if text_content := block.text.strip():
                        # Use rich's markup escaping for user-generated content
                        escaped_text = text_content.replace("[", "[[").replace(
                            "]", "]]"
                        )

                        # Update live display if available
                        if hasattr(self, "_live_display") and self._live_display:
                            # Build current display content
                            display_lines: list[str] = []
                            if self._current_tool_info:
                                display_lines.extend(self._current_tool_info)
                            display_lines.append(
                                f"[grey50]💭 Thinking: {escaped_text[:100]}...[/grey50]"
                            )
                            # Use create_agent_panel for consistency
                            panel = display.create_agent_panel(
                                self.name, "\n".join(display_lines)
                            )
                            self._live_display.update(panel)
                        else:
                            display.print(
                                f"  [grey50]Coder: {escaped_text[:150]}...[/grey50]"
                            )
                elif isinstance(block, ToolUseBlock):
                    # Format tool usage information
                    tool_info = [
                        f"[bold yellow]🔧 Tool Use:[/bold yellow] [bold magenta]{block.name}[/bold magenta]"
                    ]
                    for key, value in block.input.items():
                        escaped_value = str(value).replace("[", "[[").replace("]", "]]")
                        tool_info.append(
                            f"  [green]{key}:[/green] {escaped_value[:200]}"
                        )

                    # Update live display if available
                    if hasattr(self, "_live_display") and self._live_display:
                        self._current_tool_info = tool_info
                        # Use create_agent_panel for consistency
                        panel = display.create_agent_panel(
                            self.name, "\n".join(tool_info)
                        )
                        self._live_display.update(panel)
                    else:
                        for line in tool_info:
                            display.print(f"  {line}")
        elif isinstance(message, ResultMessage) and message.is_error:
            error_msg = f"[bold red]❌ Result: Error ({message.subtype})[/bold red]"

            # Update live display if available
            if hasattr(self, "_live_display") and self._live_display:
                error_display_lines: list[str] = []
                if self._current_tool_info:
                    error_display_lines.extend(self._current_tool_info)
                error_display_lines.append(error_msg)
                # Use create_agent_panel for consistency
                panel = display.create_agent_panel(
                    self.name, "\n".join(error_display_lines)
                )
                self._live_display.update(panel)
                # Clear the current tool info after showing error
                self._current_tool_info = []
            else:
                display.print(f"  {error_msg}")
