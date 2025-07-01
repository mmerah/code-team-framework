from claude_code_sdk import (
    AssistantMessage,
    Message,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from rich.console import Console

from code_team.agents.base import Agent


class Coder(Agent):
    """Executes a detailed prompt to modify the codebase."""

    async def run(  # type: ignore[override]
        self, coder_prompt: str, verification_feedback: str | None = None
    ) -> bool:
        """
        Runs the Coder agent to perform code modifications.

        Args:
            coder_prompt: The detailed instructions from the Prompter.
            verification_feedback: Optional feedback from a previous failed run.

        Returns:
            True if the process completed, False otherwise.
        """
        system_prompt = self.templates.render(
            "CODER_INSTRUCTIONS.md",
            VERIFICATION_FEEDBACK=verification_feedback
            or "No feedback from previous run.",
        )

        prompt = (
            "Here are your instructions. Follow them carefully and log your actions."
        )

        allowed_tools = ["Read", "Write", "Bash"]

        # Using the SDK's query function to run the agentic Coder
        llm_stream = self.llm.query(
            prompt=prompt,
            system_prompt=coder_prompt + "\n\n" + system_prompt,
            allowed_tools=allowed_tools,
        )

        # Custom streaming for Coder since it needs to handle ResultMessage differently
        async for message in llm_stream:
            # Let the base class handle AssistantMessage and other message types
            # by manually calling the streaming logic without the "finished" message
            await self._handle_coder_message(message)

        return True

    async def _handle_coder_message(self, message: Message) -> None:
        """Handle individual messages from the Coder's LLM stream."""
        console = Console()

        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    if text_content := block.text.strip():
                        # Use rich's markup escaping for user-generated content
                        escaped_text = text_content.replace("[", "[[").replace(
                            "]", "]]"
                        )
                        console.print(
                            f"  [grey50]Coder: {escaped_text[:150]}...[/grey50]"
                        )
                elif isinstance(block, ToolUseBlock):
                    console.print(
                        f"  [bold yellow]↳ Tool Use:[/bold yellow] [bold magenta]{block.name}[/bold magenta]"
                    )
                    for key, value in block.input.items():
                        escaped_value = str(value).replace("[", "[[").replace("]", "]]")
                        console.print(
                            f"    [green]{key}:[/green] {escaped_value[:200]}"
                        )
        elif isinstance(message, ResultMessage) and message.is_error:
            console.print(f"  [bold red]Result: Error ({message.subtype})[/bold red]")
