from claude_code_sdk import AssistantMessage, TextBlock

from code_team.agents.base import Agent
from code_team.models.plan import Task


class Prompter(Agent):
    """Generates a detailed, context-rich prompt for the Coder agent."""

    async def run(self, task: Task) -> str:  # type: ignore[override]
        """
        Creates a prompt for a given task.

        Args:
            task: The task to generate a prompt for.

        Returns:
            A detailed prompt string for the Coder agent.
        """
        print(f"Prompter: Generating detailed instructions for task '{task.id}'...")
        system_prompt = self.templates.render("PROMPTER_INSTRUCTIONS.md")
        prompt = f"Generate the coder prompt for this task:\nID: {task.id}\nDescription: {task.description}"

        coder_prompt = ""
        async for message in self.llm.query(prompt=prompt, system_prompt=system_prompt):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        coder_prompt += block.text

        print(f"Prompter: Instructions for '{task.id}' generated.")
        return coder_prompt.strip()
