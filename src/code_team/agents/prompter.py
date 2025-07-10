from pathlib import Path

from code_team.agents.base import Agent
from code_team.models.plan import Task
from code_team.utils import filesystem


class Prompter(Agent):
    """Generates a detailed, context-rich prompt for the Coder agent."""

    async def run(self, task: Task, plan_id: str) -> Path:  # type: ignore[override]
        """
        Creates a prompt for a given task and saves it to a file.

        Args:
            task: The task to generate a prompt for.
            plan_id: The ID of the current plan.

        Returns:
            Path to the newly created prompt file.
        """
        system_prompt = self.templates.render("PROMPTER_INSTRUCTIONS.md")
        prompt = f"Generate the coder prompt for this task:\nID: {task.id}\nDescription: {task.description}"

        coder_prompt = await self._robust_llm_query(
            prompt=prompt, system_prompt=system_prompt
        )

        # Save the prompt to a file in the plan directory
        plan_dir = self.project_root / self.config.paths.plan_dir / plan_id
        prompt_file = plan_dir / f"{task.id}-prompt.md"
        filesystem.write_file(prompt_file, coder_prompt)

        return prompt_file
