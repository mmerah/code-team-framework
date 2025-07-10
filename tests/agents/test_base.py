"""Unit tests for base agent class."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from claude_code_sdk import (
    AssistantMessage,
    Message,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from code_team.agents.base import Agent
from code_team.models.config import CodeTeamConfig
from code_team.utils.llm import LLMProvider
from code_team.utils.templates import TemplateManager


class ConcreteAgent(Agent):
    """Concrete implementation of Agent for testing."""

    async def run(self, **kwargs: Any) -> str:
        """Test implementation of run method."""
        return "test_result"


class TestAgent:
    """Test the Agent base class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_llm = Mock(spec=LLMProvider)
        self.mock_templates = Mock(spec=TemplateManager)
        self.mock_config = Mock(spec=CodeTeamConfig)
        self.project_root = Path("/test/project")

        self.agent = ConcreteAgent(
            llm_provider=self.mock_llm,
            template_manager=self.mock_templates,
            config=self.mock_config,
            project_root=self.project_root,
        )

    def test_initialization(self) -> None:
        """Test agent initialization."""
        assert self.agent.llm == self.mock_llm
        assert self.agent.templates == self.mock_templates
        assert self.agent.config == self.mock_config
        assert self.agent.project_root == self.project_root

    def test_name_property(self) -> None:
        """Test that name property returns class name."""
        assert self.agent.name == "ConcreteAgent"

    @pytest.mark.asyncio
    @patch("code_team.agents.base.Live")
    @patch("code_team.agents.base.display")
    async def test_stream_and_collect_response_text_only(
        self, mock_display: Mock, mock_live: Mock
    ) -> None:
        """Test streaming and collecting text-only response."""
        # Mock the Live context manager
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance

        # Mock messages
        text_block = TextBlock(text="This is a test response")
        message = AssistantMessage(content=[text_block])

        async def mock_stream() -> AsyncIterator[Message]:
            yield message

        result = await self.agent._stream_and_collect_response(mock_stream())

        assert result == "This is a test response"
        # Verify panels were created
        assert (
            mock_display.create_agent_panel.called
            or mock_display.create_scrollable_panel.called
        )

    @pytest.mark.asyncio
    @patch("code_team.agents.base.Live")
    @patch("code_team.agents.base.display")
    async def test_stream_and_collect_response_with_tools(
        self, mock_display: Mock, mock_live: Mock
    ) -> None:
        """Test streaming response with tool use."""
        # Mock the Live context manager
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance

        text_block = Mock(spec=TextBlock)
        text_block.text = "I'll use a tool"

        tool_block = Mock(spec=ToolUseBlock)
        tool_block.name = "Read"
        tool_block.input = {"file_path": "/test/file.py"}

        message = Mock(spec=AssistantMessage)
        message.content = [text_block, tool_block]

        async def mock_stream() -> AsyncIterator[Message]:
            yield message

        result = await self.agent._stream_and_collect_response(mock_stream())

        assert result == "I'll use a tool"
        # Verify panels were created
        assert (
            mock_display.create_agent_panel.called
            or mock_display.create_scrollable_panel.called
        )

    @pytest.mark.asyncio
    @patch("code_team.agents.base.Live")
    @patch("code_team.agents.base.display")
    async def test_stream_and_collect_response_with_error(
        self, mock_display: Mock, mock_live: Mock
    ) -> None:
        """Test streaming response with error result."""
        # Mock the Live context manager
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance

        text_block = Mock(spec=TextBlock)
        text_block.text = "Some text"

        text_message = Mock(spec=AssistantMessage)
        text_message.content = [text_block]

        error_message = Mock(spec=ResultMessage)
        error_message.is_error = True
        error_message.subtype = "CommandError"

        async def mock_stream() -> AsyncIterator[Message]:
            yield text_message
            yield error_message

        result = await self.agent._stream_and_collect_response(mock_stream())

        assert result == "Some text"
        # Verify panels were created
        assert (
            mock_display.create_agent_panel.called
            or mock_display.create_scrollable_panel.called
        )

    @pytest.mark.asyncio
    @patch("code_team.agents.base.Live")
    @patch("code_team.agents.base.display")
    async def test_stream_and_collect_response_multiple_messages(
        self, mock_display: Mock, mock_live: Mock
    ) -> None:
        """Test streaming multiple messages."""
        # Mock the Live context manager
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance

        text_block1 = TextBlock(text="First part ")
        text_block2 = TextBlock(text="second part.")
        message1 = AssistantMessage(content=[text_block1])
        message2 = AssistantMessage(content=[text_block2])

        async def mock_stream() -> AsyncIterator[Message]:
            yield message1
            yield message2

        result = await self.agent._stream_and_collect_response(mock_stream())

        assert result == "First part second part."

    @pytest.mark.asyncio
    @patch("code_team.agents.base.Live")
    @patch("code_team.agents.base.display")
    async def test_stream_and_collect_response_empty_stream(
        self, mock_display: Mock, mock_live: Mock
    ) -> None:
        """Test streaming empty response."""
        # Mock the Live context manager
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance

        async def mock_stream() -> AsyncIterator[Message]:
            return
            yield  # unreachable but needed for AsyncIterator type

        result = await self.agent._stream_and_collect_response(mock_stream())

        assert result == ""
        # Verify create_agent_panel was called at least once (for initial "Thinking..." panel)
        mock_display.create_agent_panel.assert_called()

    @pytest.mark.asyncio
    @patch("code_team.agents.base.Live")
    @patch("code_team.agents.base.display")
    async def test_stream_and_collect_response_markup_escaping(
        self, mock_display: Mock, mock_live: Mock
    ) -> None:
        """Test that markup characters are properly escaped."""
        # Mock the Live context manager
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance

        text_block = TextBlock(text="Text with [markup] and [/markup]")
        message = AssistantMessage(content=[text_block])

        async def mock_stream() -> AsyncIterator[Message]:
            yield message

        result = await self.agent._stream_and_collect_response(mock_stream())

        assert result == "Text with [markup] and [/markup]"
        # Verify create_scrollable_panel was called with escaped content
        mock_display.create_scrollable_panel.assert_called()
        # Get the last call to create_scrollable_panel
        call_args = mock_display.create_scrollable_panel.call_args
        # The content_lines should contain the escaped markup
        content_lines = call_args[0][1]  # Second positional argument
        assert len(content_lines) == 1
        assert "[[markup]]" in content_lines[0]
        assert "[[/markup]]" in content_lines[0]

    @pytest.mark.asyncio
    @patch("code_team.agents.base.Live")
    @patch("code_team.agents.base.display")
    async def test_stream_and_collect_response_tool_value_escaping(
        self, mock_display: Mock, mock_live: Mock
    ) -> None:
        """Test that tool input values are properly escaped."""
        # Mock the Live context manager
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance

        tool_block = Mock(spec=ToolUseBlock)
        tool_block.name = "Write"
        tool_block.input = {"content": "Content with [markup] here"}

        message = Mock(spec=AssistantMessage)
        message.content = [tool_block]

        async def mock_stream() -> AsyncIterator[Message]:
            yield message

        await self.agent._stream_and_collect_response(mock_stream())

        # Verify create_scrollable_panel was called with escaped content
        mock_display.create_scrollable_panel.assert_called()
        # Get the call args to verify tool value escaping
        call_args = mock_display.create_scrollable_panel.call_args
        content_lines = call_args[0][1]  # Second positional argument
        # Should have tool use line and parameter line
        assert any("[[markup]]" in line for line in content_lines)

    @pytest.mark.asyncio
    async def test_run_method_abstract(self) -> None:
        """Test that run method is properly implemented in concrete class."""
        result = await self.agent.run(test_param="value")
        assert result == "test_result"
