from typing import Any

from claude_code_sdk import AssistantMessage, TextBlock

from code_team.agents.base import Agent
from code_team.models.plan import Task


class CodeVerifier(Agent):
    """A generic agent for verifying code against a specific set of criteria."""

    def __init__(self, verifier_type: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.verifier_type = verifier_type
        self.instruction_file = f"VERIFIER_{verifier_type.upper()}_INSTRUCTIONS.md"

    async def run(self, task: Task, diff: str) -> str:  # type: ignore[override]
        """
        Runs the verifier on the provided code changes.

        Args:
            task: The task that was just completed.
            diff: The git diff of the changes made.

        Returns:
            A formatted PASS/FAIL report.
        """
        print(
            f"Verifier ({self.verifier_type}): Analyzing code changes for task '{task.id}'..."
        )
        system_prompt = self.templates.render(
            self.instruction_file,
            TASK_ID=task.id,
            TASK_DESCRIPTION=task.description,
        )
        prompt = f"""
        Here are the code changes to review for task '{task.id}':

        ```diff
        {diff}
        ```

        Please provide your verification report in the specified PASS/FAIL format.
        """

        report = ""
        async for message in self.llm.query(prompt=prompt, system_prompt=system_prompt):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        report += block.text

        return report.strip()
