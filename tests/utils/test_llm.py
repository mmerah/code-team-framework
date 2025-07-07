"""Unit tests for LLM utilities."""

from collections.abc import AsyncIterator
from unittest.mock import Mock, patch

import pytest
from claude_code_sdk import AssistantMessage, Message, TextBlock

from code_team.models.config import LLMConfig
from code_team.utils.llm import LLMProvider


class TestLLMProvider:
    """Test the LLMProvider class."""

    def test_initialization(self) -> None:
        """Test LLMProvider initialization."""
        config = LLMConfig(planner="opus")
        cwd = "/test/path"

        provider = LLMProvider(config, cwd)

        assert provider._config == config
        assert provider._cwd == cwd

    def test_initialization_with_default_config(self) -> None:
        """Test LLMProvider initialization with default config."""
        config = LLMConfig()
        cwd = "/test/path"

        provider = LLMProvider(config, cwd)

        # Default model
        assert provider._config.planner == "sonnet"
        assert provider._config.coder == "sonnet"
        assert provider._cwd == cwd

    @pytest.mark.asyncio
    @patch("code_team.utils.llm.query")
    async def test_query_basic(self, mock_query: Mock) -> None:
        """Test basic query functionality."""

        async def mock_messages() -> AsyncIterator[Message]:
            msg1 = AssistantMessage(content=[TextBlock(text="Response 1")])
            msg2 = AssistantMessage(content=[TextBlock(text="Response 2")])
            yield msg1
            yield msg2

        mock_query.return_value = mock_messages()

        config = LLMConfig(planner="opus")
        provider = LLMProvider(config, "/test/path")

        messages = []
        async for message in provider.query(
            prompt="Test prompt", system_prompt="Test system prompt"
        ):
            messages.append(message)

        assert len(messages) == 2
        assert isinstance(messages[0], AssistantMessage)
        assert isinstance(messages[1], AssistantMessage)
        assert len(messages[0].content) == 1
        assert isinstance(messages[0].content[0], TextBlock)
        assert messages[0].content[0].text == "Response 1"
        assert len(messages[1].content) == 1
        assert isinstance(messages[1].content[0], TextBlock)
        assert messages[1].content[0].text == "Response 2"

    @pytest.mark.asyncio
    @patch("code_team.utils.llm.query")
    async def test_query_with_tools(self, mock_query: Mock) -> None:
        """Test query with allowed tools."""

        async def mock_messages() -> AsyncIterator[Message]:
            msg = AssistantMessage(content=[TextBlock(text="Tool response")])
            yield msg

        mock_query.return_value = mock_messages()

        config = LLMConfig()
        provider = LLMProvider(config, "/test/path")

        messages = []
        async for message in provider.query(
            prompt="Test prompt",
            system_prompt="System prompt",
            allowed_tools=["Read", "Write", "Bash"],
        ):
            messages.append(message)

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert call_args[1]["prompt"] == "Test prompt"
        assert call_args[1]["options"].allowed_tools == ["Read", "Write", "Bash"]
        assert call_args[1]["options"].model == "sonnet"
        assert call_args[1]["options"].system_prompt == "System prompt"
        assert call_args[1]["options"].cwd == "/test/path"
        assert call_args[1]["options"].permission_mode == "acceptEdits"

    @pytest.mark.asyncio
    @patch("code_team.utils.llm.query")
    async def test_query_no_tools(self, mock_query: Mock) -> None:
        """Test query without allowed tools."""

        async def mock_messages() -> AsyncIterator[Message]:
            msg = AssistantMessage(content=[TextBlock(text="No tools response")])
            yield msg

        mock_query.return_value = mock_messages()

        config = LLMConfig(coder="haiku")
        provider = LLMProvider(config, "/another/path")

        messages = []
        async for message in provider.query(
            prompt="Another prompt", system_prompt="Another system prompt"
        ):
            messages.append(message)

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert call_args[1]["options"].allowed_tools == []
        assert call_args[1]["options"].model == "sonnet"
        assert call_args[1]["options"].cwd == "/another/path"

    @pytest.mark.asyncio
    @patch("code_team.utils.llm.query")
    async def test_query_empty_response(self, mock_query: Mock) -> None:
        """Test query with empty response."""

        async def mock_messages() -> AsyncIterator[Message]:
            return
            yield  # unreachable but needed for type checker

        mock_query.return_value = mock_messages()

        config = LLMConfig()
        provider = LLMProvider(config, "/test/path")

        messages = []
        async for message in provider.query(
            prompt="Empty prompt", system_prompt="Empty system prompt"
        ):
            messages.append(message)

        assert len(messages) == 0

    @pytest.mark.asyncio
    @patch("code_team.utils.llm.query")
    async def test_query_configuration_passed_correctly(self, mock_query: Mock) -> None:
        """Test that configuration is passed correctly to Claude Code SDK."""

        async def mock_messages() -> AsyncIterator[Message]:
            msg = AssistantMessage(content=[TextBlock(text="Config test")])
            yield msg

        mock_query.return_value = mock_messages()

        config = LLMConfig(planner="opus")
        cwd = "/custom/working/directory"
        provider = LLMProvider(config, cwd)

        async for _ in provider.query(
            prompt="Config test prompt",
            system_prompt="Config test system",
            allowed_tools=["Read", "Edit"],
        ):
            pass

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        options = call_args[1]["options"]

        assert options.model == "opus"
        assert options.system_prompt == "Config test system"
        assert options.allowed_tools == ["Read", "Edit"]
        assert options.cwd == "/custom/working/directory"
        assert options.permission_mode == "acceptEdits"

    @pytest.mark.asyncio
    @patch("code_team.utils.llm.query")
    async def test_query_sdk_exception(self, mock_query: Mock) -> None:
        """Test handling of SDK exceptions."""
        mock_query.side_effect = Exception("SDK Error")

        config = LLMConfig()
        provider = LLMProvider(config, "/test/path")

        with pytest.raises(Exception) as exc_info:
            async for _ in provider.query("Test", "System"):
                pass

        assert "SDK Error" in str(exc_info.value)
