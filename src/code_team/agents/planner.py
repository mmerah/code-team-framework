from claude_code_sdk import AssistantMessage, TextBlock

from code_team.agents.base import Agent
from code_team.utils import filesystem, parsing


class Planner(Agent):
    """Collaborates with the user to create a detailed implementation plan."""

    async def run(self, initial_request: str) -> dict[str, str]:  # type: ignore[override]
        """
        Runs an interactive planning session with the user.

        Args:
            initial_request: The user's high-level feature request.

        Returns:
            A dictionary containing the content for `plan.yml` and
            `ACCEPTANCE_CRITERIA.md`.
        """
        print(
            "Planner: Hello! Let's create a plan. To start, I need to understand the project structure."
        )
        repo_map = filesystem.get_repo_map(self.project_root)
        filesystem.write_file(
            self.project_root / "config/agent_instructions/REPO_MAP.md", repo_map
        )

        print(
            f"Planner: Based on your request '{initial_request}', I'll ask some clarifying questions."
        )

        conversation_history = [f"User request: {initial_request}"]
        prompt = initial_request

        while True:
            system_prompt = self.templates.render("PLANNER_INSTRUCTIONS.md")
            full_prompt = (
                "\n".join(conversation_history) + f"\n\nPlanner (to user): {prompt}"
            )

            response_text = await self._get_planner_response(system_prompt, full_prompt)
            print(f"\nPlanner: {response_text}")

            user_input = input("You: ").strip()

            if user_input.lower() == "/save_plan":
                return await self._generate_final_plan(conversation_history)

            conversation_history.append(f"Planner: {response_text}")
            conversation_history.append(f"User: {user_input}")
            prompt = user_input  # Next prompt is just the user's latest message

    async def _get_planner_response(self, system_prompt: str, prompt: str) -> str:
        """Gets a single response from the LLM for the planning phase."""
        response_text = ""
        async for message in self.llm.query(prompt=prompt, system_prompt=system_prompt):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
        return response_text

    async def _generate_final_plan(
        self, conversation_history: list[str]
    ) -> dict[str, str]:
        """Generates the final plan.yml and acceptance criteria files."""
        print("Planner: Understood. Generating the final plan files...")
        system_prompt = self.templates.render("PLANNER_INSTRUCTIONS.md")
        final_prompt = (
            "\n".join(conversation_history)
            + "\n\nUser: /save_plan"
            + "\n\nOkay, I have all the information. Now, generate the `plan.yml` and `ACCEPTANCE_CRITERIA.md` content as separate files."
            " First, output the full content for `plan.yml`, then a separator '---_---', then the full content for `ACCEPTANCE_CRITERIA.md`."
        )

        response_text = ""
        async for message in self.llm.query(
            prompt=final_prompt, system_prompt=system_prompt
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        parts = response_text.split("---_---")
        if len(parts) != 2:
            print(
                "Planner: I had trouble generating the plan in the correct format. Please try again."
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
