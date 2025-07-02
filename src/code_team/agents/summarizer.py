from code_team.agents.base import Agent


class Summarizer(Agent):
    """Condenses a long Coder Log to manage context window size."""

    async def run(self, log_content: str) -> str:  # type: ignore[override]
        """
        Summarizes the provided log content.

        Args:
            log_content: The full content of CODER_LOG.md.

        Returns:
            A condensed version of the log.
        """
        system_prompt = self.templates.render("SUMMARIZER_INSTRUCTIONS.md")
        prompt = f"Please summarize the following log:\n\n{log_content}"

        summary = await self._robust_llm_query(
            prompt=prompt, system_prompt=system_prompt
        )

        return summary.strip()
