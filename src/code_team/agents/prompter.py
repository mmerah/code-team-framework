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
        system_prompt = self.templates.render("PROMPTER_INSTRUCTIONS.md")
        prompt = f"Generate the coder prompt for this task:\nID: {task.id}\nDescription: {task.description}"

        coder_prompt = await self._robust_llm_query(
            prompt=prompt, system_prompt=system_prompt
        )

        return coder_prompt
