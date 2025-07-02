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
        system_prompt = self.templates.render(
            "COMMIT_INSTRUCTIONS.md",
            TASK_ID=task.id,
            TASK_DESCRIPTION=task.description,
        )
        prompt = "Generate the commit message."

        commit_message = await self._robust_llm_query(
            prompt=prompt, system_prompt=system_prompt
        )

        # Clean the message: remove potential code blocks and surrounding text
        if "```" in commit_message:
            # Simple extraction if it uses code blocks
            lines = commit_message.split("\n")
            core_message_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    core_message_lines.append(line)
            commit_message = "\n".join(core_message_lines)

        return commit_message.strip()
