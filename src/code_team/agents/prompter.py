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

        llm_stream = self.llm.query(prompt=prompt, system_prompt=system_prompt)
        coder_prompt = await self._stream_and_collect_response(llm_stream)

        return coder_prompt
