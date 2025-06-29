from claude_code_sdk import AssistantMessage, ResultMessage, TextBlock

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
        print(
            "Coder: Starting work on the current task. See .codeteam/logs/CODER_LOG.md for details."
        )

        system_prompt = self.templates.render(
            "CODER_INSTRUCTIONS.md",
            VERIFICATION_FEEDBACK=verification_feedback
            or "No feedback from previous run.",
        )

        prompt = (
            "Here are your instructions. Follow them carefully and log your actions."
        )

        allowed_tools = ["Read", "Write", "Bash"]
        final_message = ""

        # Using the SDK's query function to run the agentic Coder
        async for message in self.llm.query(
            prompt=prompt,
            system_prompt=coder_prompt + "\n\n" + system_prompt,
            allowed_tools=allowed_tools,
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # We can print coder's "thoughts" or actions here if needed
                        print(f"Coder thought: {block.text[:100]}...")
            elif isinstance(message, ResultMessage):
                final_message = message.result or "Completed"

        print(f"Coder: Task execution finished. Result: {final_message}")
        return True
