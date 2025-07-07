from collections.abc import AsyncIterator

from claude_code_sdk import ClaudeCodeOptions, Message, query

from code_team.models.config import LLMConfig


class LLMProvider:
    """A wrapper around the Claude Code SDK for standardized LLM calls."""

    def __init__(self, config: LLMConfig, cwd: str):
        self._config = config
        self._cwd = cwd

    async def query(
        self,
        prompt: str,
        system_prompt: str,
        allowed_tools: list[str] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[Message]:
        """
        Perform a query using the Claude Code SDK.

        Args:
            prompt: The user-level prompt for the current turn.
            system_prompt: The detailed system prompt guiding the agent.
            allowed_tools: A list of tools the agent can use (e.g., ["Read", "Write"]).
            model: The model to use for this query. If None, uses the planner model as default.

        Yields:
            Messages from the SDK's response stream.
        """
        options = ClaudeCodeOptions(
            model=model
            or self._config.planner,  # Use planner model as default fallback
            system_prompt=system_prompt,
            allowed_tools=allowed_tools or [],
            cwd=self._cwd,
            permission_mode="acceptEdits",  # Use with caution, good for agentic work
        )

        # The SDK's query function is the main entry point.
        # It's an async generator, so we yield from it.
        async for message in query(prompt=prompt, options=options):
            yield message
