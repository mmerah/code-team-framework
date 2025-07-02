from typing import Any

from code_team.agents.base import Agent
from code_team.models.plan import Task


class CodeVerifier(Agent):
    """A generic agent for verifying code against a specific set of criteria."""

    def __init__(self, verifier_type: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.verifier_type = verifier_type
        self.instruction_file = self._get_instruction_filename(verifier_type)

    def _get_instruction_filename(self, verifier_type: str) -> str:
        """Maps verifier types to their corresponding instruction filenames."""
        mapping = {
            "architecture": "VERIFIER_ARCH_INSTRUCTIONS.md",
            "task_completion": "VERIFIER_TASK_INSTRUCTIONS.md",
            "security": "VERIFIER_SEC_INSTRUCTIONS.md",
            "performance": "VERIFIER_PERF_INSTRUCTIONS.md",
        }

        if verifier_type not in mapping:
            raise ValueError(f"Unknown verifier type: {verifier_type}")

        return mapping[verifier_type]

    @property
    def name(self) -> str:
        """Returns the verifier's specific name including type."""
        return f"{self.__class__.__name__} ({self.verifier_type})"

    async def run(self, task: Task, diff: str) -> str:  # type: ignore[override]
        """
        Runs the verifier on the provided code changes.

        Args:
            task: The task that was just completed.
            diff: The git diff of the changes made.

        Returns:
            A formatted PASS/FAIL report.
        """
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

        report = await self._robust_llm_query(
            prompt=prompt, system_prompt=system_prompt
        )

        return report.strip()
