from typing import Any

from code_team.agents.base import Agent
from code_team.utils import parsing
from code_team.utils.ui import display, interactive


class Planner(Agent):
    """Collaborates with the user to create a detailed implementation plan."""

    async def run(self, **kwargs: Any) -> dict[str, str]:
        """
        Runs an interactive planning session with the user.

        Args:
            **kwargs: Keyword arguments containing:
                - initial_request: The user's high-level feature request.
                - plan_id: The ID for the plan being created (optional).

        Returns:
            A dictionary containing the content for `plan.yml` and
            `ACCEPTANCE_CRITERIA.md`.
        """
        initial_request: str = kwargs["initial_request"]
        plan_id: str | None = kwargs.get("plan_id")
        display.agent_thought(
            "Planner",
            "Hello! Let's create a plan. To start, I need to understand the project structure.",
        )

        display.agent_thought(
            "Planner",
            f"Based on your request '{initial_request}', I'll ask some clarifying questions.",
        )

        conversation_history = [f"User request: {initial_request}"]
        prompt = initial_request

        while True:
            system_prompt = self.templates.render(
                "PLANNER_INSTRUCTIONS.md", PLAN_ID=plan_id or "unknown"
            )
            full_prompt = (
                "\n".join(conversation_history) + f"\n\nPlanner (to user): {prompt}"
            )

            response_text = await self._get_planner_response(system_prompt, full_prompt)

            # Check if response contains the file separator (plan generation)
            if "===FILE_SEPARATOR===" in response_text:
                return self._parse_plan_files(response_text)

            display.agent_thought("Planner", response_text)

            user_input = interactive.get_text_input("You").strip()

            conversation_history.append(f"Planner: {response_text}")
            conversation_history.append(f"User: {user_input}")
            prompt = user_input  # Next prompt is just the user's latest message

    async def _get_planner_response(self, system_prompt: str, prompt: str) -> str:
        """Gets a single response from the LLM with robust error handling."""
        return await self._robust_llm_query(prompt=prompt, system_prompt=system_prompt)

    def _parse_plan_files(self, response_text: str) -> dict[str, str]:
        """Parses the plan files from the response text."""
        parts = response_text.split("===FILE_SEPARATOR===")
        if len(parts) != 2:
            display.error(
                "Failed to generate plan in the correct format. Please try again."
            )
            return {}

        plan_yaml = parsing.extract_code_block(parts[0], "yaml") or parts[0].strip()
        acceptance_md = (
            parsing.extract_code_block(parts[1], "markdown") or parts[1].strip()
        )

        return {
            "plan.yml": plan_yaml,
            "ACCEPTANCE_CRITERIA.md": acceptance_md,
        }
