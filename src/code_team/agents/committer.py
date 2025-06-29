from claude_code_sdk import AssistantMessage, TextBlock

from code_team.agents.base import Agent
from code_team.models.plan import Task


class Committer(Agent):
    """Generates a conventional commit message for a completed task."""

    async def run(self, task: Task) -> str:  # type: ignore[override]
        """
        Generates a commit message.

        Args:
            task: The completed task.

        Returns:
            A formatted commit message string.
        """
        print(f"Committer: Generating commit message for task '{task.id}'...")
        system_prompt = self.templates.render(
            "COMMIT_INSTRUCTIONS.md",
            TASK_ID=task.id,
            TASK_DESCRIPTION=task.description,
        )
        prompt = "Generate the commit message."

        commit_message = ""
        async for message in self.llm.query(prompt=prompt, system_prompt=system_prompt):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        commit_message += block.text

        return commit_message.strip()
