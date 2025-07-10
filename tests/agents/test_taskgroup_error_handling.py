"""Test TaskGroup error handling in agents without using real LLM calls."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from claude_code_sdk import AssistantMessage, ResultMessage, TextBlock

from code_team.agents.planner import Planner
from code_team.models.config import (
    CodeTeamConfig,
    LLMConfig,
    VerificationConfig,
    VerifierInstances,
)
from code_team.utils.exceptions import ExceptionGroup
from code_team.utils.llm import LLMProvider
from code_team.utils.templates import TemplateManager


class MockMessage:
    """Mock message for testing."""

    def __init__(self, content: str) -> None:
        self.content = [TextBlock(text=content)]


async def mock_llm_stream_success() -> AsyncIterator[Any]:
    """Mock successful LLM stream."""
    yield AssistantMessage(content=[TextBlock(text="Hello, I can help you with that.")])
    yield AssistantMessage(content=[TextBlock(text=" Let me create a plan for you.")])
    yield ResultMessage(
        subtype="success",
        duration_ms=1000,
        duration_api_ms=900,
        is_error=False,
        num_turns=1,
        session_id="test",
        total_cost_usd=0.01,
        usage={},
        result="Success",
    )


async def mock_llm_stream_taskgroup_error() -> AsyncIterator[Any]:
    """Mock LLM stream that raises TaskGroup error."""
    yield AssistantMessage(content=[TextBlock(text="Starting to process...")])
    # Simulate the TaskGroup error that was happening
    raise ExceptionGroup(
        "unhandled errors in a TaskGroup (1 sub-exception)",
        [ValueError("Failed to decode JSON: truncated response")],
    )


async def mock_llm_stream_partial_response() -> AsyncIterator[Any]:
    """Mock LLM stream that provides partial response before error."""
    yield AssistantMessage(content=[TextBlock(text="I can help you improve")])
    yield AssistantMessage(content=[TextBlock(text=" your code comments by")])
    # Then error occurs
    raise ExceptionGroup(
        "unhandled errors in a TaskGroup (1 sub-exception)",
        [ValueError("JSON decode error")],
    )


async def mock_llm_stream_with_content(content: str) -> AsyncIterator[Any]:
    """Mock LLM stream with specific content."""
    yield AssistantMessage(content=[TextBlock(text=content)])
    yield ResultMessage(
        subtype="success",
        duration_ms=1000,
        duration_api_ms=900,
        is_error=False,
        num_turns=1,
        session_id="test",
        total_cost_usd=0.01,
        usage={},
        result="Success",
    )


@pytest.fixture
def mock_config() -> CodeTeamConfig:
    """Create a mock configuration."""
    return CodeTeamConfig(
        llm=LLMConfig(),
        verification=VerificationConfig(),
        verifier_instances=VerifierInstances(),
    )


@pytest.fixture
def mock_template_manager() -> Mock:
    """Create a mock template manager."""
    manager = Mock(spec=TemplateManager)
    manager.render.return_value = "Mock system prompt"
    return manager


@pytest.fixture
def mock_llm_provider() -> Mock:
    """Create a mock LLM provider."""
    return Mock(spec=LLMProvider)


@pytest.fixture
def test_agent(
    mock_llm_provider: Mock, mock_template_manager: Mock, mock_config: CodeTeamConfig
) -> Planner:
    """Create a test agent instance."""
    return Planner(
        mock_llm_provider, mock_template_manager, mock_config, Path("/tmp/test")
    )


@pytest.fixture
def fast_agent(test_agent: Planner) -> Planner:
    """Create agent with no retry delay for testing."""
    test_agent.retry_delay = 0.0
    return test_agent


class TestTaskGroupErrorHandling:
    """Test TaskGroup error handling in agents."""

    @pytest.mark.asyncio
    async def test_successful_stream_processing(
        self, test_agent: Planner, mock_llm_provider: Mock
    ) -> None:
        """Test that successful streams work correctly."""
        mock_llm_provider.query.return_value = mock_llm_stream_success()

        response = await test_agent._robust_llm_query(
            prompt="Test prompt", system_prompt="Test system prompt"
        )

        assert (
            "Hello, I can help you with that. Let me create a plan for you." in response
        )
        mock_llm_provider.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_taskgroup_error_handling_with_retries(
        self, fast_agent: Planner, mock_llm_provider: Mock
    ) -> None:
        """Test that TaskGroup errors are handled with retries."""
        # Create a counter to track calls
        call_count = 0

        def mock_query_side_effect(*args: Any, **kwargs: Any) -> AsyncIterator[Any]:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return mock_llm_stream_taskgroup_error()
            else:
                return mock_llm_stream_success()

        mock_llm_provider.query.side_effect = mock_query_side_effect

        response = await fast_agent._robust_llm_query(
            prompt="Test prompt", system_prompt="Test system prompt"
        )

        # Should get successful response after retries
        assert "Hello, I can help you with that" in response
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_taskgroup_error_exhausts_retries(
        self, fast_agent: Planner, mock_llm_provider: Mock
    ) -> None:
        """Test that TaskGroup errors result in fallback after max retries."""
        # All attempts fail
        mock_llm_provider.query.side_effect = (
            lambda *args: mock_llm_stream_taskgroup_error()
        )

        response = await fast_agent._robust_llm_query(
            prompt="clarifying questions about the project",
            system_prompt="Test system prompt",
        )

        # Should get fallback response
        assert "I'd be happy to help create a plan" in response
        assert mock_llm_provider.query.call_count == 3

    @pytest.mark.asyncio
    async def test_partial_response_collection(
        self, fast_agent: Planner, mock_llm_provider: Mock
    ) -> None:
        """Test that partial responses are collected before errors."""
        mock_llm_provider.query.side_effect = (
            lambda *args: mock_llm_stream_partial_response()
        )

        response = await fast_agent._robust_llm_query(
            prompt="Test prompt", system_prompt="Test system prompt"
        )

        # Since all retries fail, it should get fallback response
        assert response is not None
        assert len(response) > 0
        # Should be the fallback response since all retries failed
        assert "technical issue" in response

    @pytest.mark.asyncio
    async def test_stream_and_collect_response_handles_exception_group(
        self, test_agent: Planner
    ) -> None:
        """Test that _stream_and_collect_response handles ExceptionGroup properly."""

        # Create a mock stream that raises ExceptionGroup
        async def mock_failing_stream() -> AsyncIterator[Any]:
            yield AssistantMessage(content=[TextBlock(text="Partial content")])
            raise ExceptionGroup("test error", [ValueError("test exception")])

        # Should re-raise the ExceptionGroup for retry logic to handle
        with pytest.raises(ExceptionGroup):
            await test_agent._stream_and_collect_response(mock_failing_stream())

    @pytest.mark.asyncio
    async def test_fallback_responses_are_contextual(
        self, fast_agent: Planner, mock_llm_provider: Mock
    ) -> None:
        """Test that fallback responses are contextual based on prompt content."""
        mock_llm_provider.query.side_effect = ExceptionGroup(
            "test", [ValueError("test")]
        )

        # Test plan generation fallback
        response = await fast_agent._robust_llm_query(
            prompt="Generate plan.yml content", system_prompt="Test"
        )
        assert "plan files" in response.lower()

        # Test clarifying questions fallback
        response = await fast_agent._robust_llm_query(
            prompt="I need clarifying questions about the project", system_prompt="Test"
        )
        assert "more details" in response.lower()

    def test_get_fallback_response_plan_context(self, test_agent: Planner) -> None:
        """Test fallback response for plan generation context."""
        response = test_agent._get_fallback_response("Generate the plan.yml file")
        assert "plan files" in response
        assert "technical issue" in response

    def test_get_fallback_response_clarifying_questions_context(
        self, test_agent: Planner
    ) -> None:
        """Test fallback response for clarifying questions context."""
        response = test_agent._get_fallback_response("Ask clarifying questions")
        assert "more details" in response
        assert "goals and requirements" in response

    def test_get_fallback_response_generic(self, test_agent: Planner) -> None:
        """Test fallback response for generic context."""
        response = test_agent._get_fallback_response("Some random prompt")
        assert "technical issue" in response
        assert "AI service connection" in response


class TestPlannerSpecificErrorHandling:
    """Test error handling specific to the Planner agent."""

    @pytest.mark.asyncio
    async def test_planner_get_response_uses_robust_query(
        self, test_agent: Planner, mock_llm_provider: Mock
    ) -> None:
        """Test that planner's _get_planner_response uses the robust query method."""
        mock_llm_provider.query.return_value = mock_llm_stream_success()

        response = await test_agent._get_planner_response(
            system_prompt="Test system prompt", prompt="Test prompt"
        )

        assert response is not None
        assert len(response) > 0
        mock_llm_provider.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_planner_parse_plan_files(
        self, test_agent: Planner, mock_llm_provider: Mock
    ) -> None:
        """Test that planner correctly parses plan files from response."""
        # Test the _parse_plan_files method directly
        response_with_files = (
            "plan content\n===FILE_SEPARATOR===\nacceptance criteria content"
        )

        result = test_agent._parse_plan_files(response_with_files)

        assert "plan.yml" in result
        assert "ACCEPTANCE_CRITERIA.md" in result
        assert result["plan.yml"] == "plan content"
        assert result["ACCEPTANCE_CRITERIA.md"] == "acceptance criteria content"
