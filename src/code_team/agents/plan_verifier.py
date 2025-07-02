from code_team.agents.base import Agent


class PlanVerifier(Agent):
    """Critically reviews a generated plan for flaws."""

    async def run(self, plan_content: str, acceptance_criteria: str) -> str:  # type: ignore[override]
        """
        Verifies a plan and returns feedback.

        Args:
            plan_content: The YAML content of the plan.
            acceptance_criteria: The content of the acceptance criteria markdown.

        Returns:
            A string containing the verification feedback.
        """
        system_prompt = self.templates.render("PLAN_VERIFIER_INSTRUCTIONS.md")
        prompt = f"""
        Here is the plan to verify:

        ## plan.yml
        ```yaml
        {plan_content}
        ```

        ## ACCEPTANCE_CRITERIA.md
        ```markdown
        {acceptance_criteria}
        ```

        Please perform a critical review and provide your feedback in the specified format.
        """

        feedback = await self._robust_llm_query(
            prompt=prompt, system_prompt=system_prompt
        )

        return feedback.strip()
