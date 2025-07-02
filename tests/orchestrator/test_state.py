"""Unit tests for orchestrator state."""

import pytest

from code_team.orchestrator.state import OrchestratorState


class TestOrchestratorState:
    """Test the OrchestratorState enum."""

    def test_all_states_exist(self) -> None:
        """Test that all expected states are defined."""
        expected_states = {
            "IDLE",
            "PLANNING_DRAFTING",
            "PLANNING_AWAITING_REVIEW",
            "PLANNING_VERIFYING",
            "CODING_AWAITING_TASK_SELECTION",
            "CODING_PROMPTING",
            "CODING_IN_PROGRESS",
            "VERIFYING",
            "AWAITING_VERIFICATION_REVIEW",
            "COMMITTING",
            "PLAN_COMPLETE",
            "HALTED_FOR_ERROR",
        }

        actual_states = {state.name for state in OrchestratorState}
        assert actual_states == expected_states

    def test_state_values_are_unique(self) -> None:
        """Test that all state values are unique."""
        values = [state.value for state in OrchestratorState]
        assert len(values) == len(set(values))

    def test_state_values_are_auto_generated(self) -> None:
        """Test that state values are auto-generated integers."""
        for state in OrchestratorState:
            assert isinstance(state.value, int)
            assert state.value > 0

    def test_idle_state(self) -> None:
        """Test IDLE state."""
        assert OrchestratorState.IDLE.name == "IDLE"
        assert isinstance(OrchestratorState.IDLE.value, int)

    def test_planning_states(self) -> None:
        """Test planning-related states."""
        planning_states = [
            OrchestratorState.PLANNING_DRAFTING,
            OrchestratorState.PLANNING_AWAITING_REVIEW,
            OrchestratorState.PLANNING_VERIFYING,
        ]

        for state in planning_states:
            assert "PLANNING" in state.name
            assert isinstance(state.value, int)

    def test_coding_states(self) -> None:
        """Test coding-related states."""
        coding_states = [
            OrchestratorState.CODING_AWAITING_TASK_SELECTION,
            OrchestratorState.CODING_PROMPTING,
            OrchestratorState.CODING_IN_PROGRESS,
        ]

        for state in coding_states:
            assert "CODING" in state.name
            assert isinstance(state.value, int)

    def test_verification_states(self) -> None:
        """Test verification-related states."""
        verification_states = [
            OrchestratorState.VERIFYING,
            OrchestratorState.AWAITING_VERIFICATION_REVIEW,
        ]

        for state in verification_states:
            assert "VERIF" in state.name
            assert isinstance(state.value, int)

    def test_terminal_states(self) -> None:
        """Test terminal states."""
        terminal_states = [
            OrchestratorState.PLAN_COMPLETE,
            OrchestratorState.HALTED_FOR_ERROR,
        ]

        for state in terminal_states:
            assert isinstance(state.value, int)

    def test_state_comparison(self) -> None:
        """Test that states can be compared."""
        state1 = OrchestratorState.IDLE
        state2 = OrchestratorState.IDLE
        state3 = OrchestratorState.PLANNING_DRAFTING

        assert state1 == state2
        assert state1 != state3

    def test_state_string_representation(self) -> None:
        """Test string representation of states."""
        state = OrchestratorState.CODING_IN_PROGRESS
        assert str(state) == "OrchestratorState.CODING_IN_PROGRESS"
        assert (
            repr(state)
            == "<OrchestratorState.CODING_IN_PROGRESS: " + str(state.value) + ">"
        )

    def test_state_from_name(self) -> None:
        """Test creating state from name."""
        state = OrchestratorState["IDLE"]
        assert state == OrchestratorState.IDLE

        state = OrchestratorState["VERIFYING"]
        assert state == OrchestratorState.VERIFYING

    def test_invalid_state_name(self) -> None:
        """Test that invalid state names raise KeyError."""
        with pytest.raises(KeyError):
            OrchestratorState["INVALID_STATE"]

    def test_state_membership(self) -> None:
        """Test checking if a value is a valid state."""
        assert OrchestratorState.IDLE in OrchestratorState
        assert "not_a_state" not in [state.name for state in OrchestratorState]

    def test_state_iteration(self) -> None:
        """Test iterating over all states."""
        states = list(OrchestratorState)
        assert len(states) == 12  # Update this number if states are added/removed
        assert OrchestratorState.IDLE in states
        assert OrchestratorState.PLAN_COMPLETE in states
