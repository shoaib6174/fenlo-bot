"""Unit tests for CallStateMachine."""

import pytest

from app.modules.voice.call_state import CallStateMachine, InvalidTransitionError


class TestCallStateMachine:
    """Test call state machine transitions and terminal state behavior."""

    def setup_method(self):
        self.sm = CallStateMachine()

    def test_valid_transition_initiated_to_ringing(self):
        """initiated → ringing via 'queued' event."""
        result = self.sm.transition("initiated", "queued")
        assert result == "ringing"

    def test_valid_transition_ringing_to_connected(self):
        """ringing → connected via 'in-progress' event."""
        result = self.sm.transition("ringing", "in-progress")
        assert result == "connected"

    def test_valid_transition_connected_to_ended(self):
        """connected → ended via 'customer-ended-call' event."""
        result = self.sm.transition("connected", "customer-ended-call")
        assert result == "ended"

    def test_invalid_transition_raises_error(self):
        """initiated → connected is not allowed."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            self.sm.transition("initiated", "in-progress")
        assert "initiated" in str(exc_info.value)
        assert "connected" in str(exc_info.value)

    def test_terminal_state_ignores_events(self):
        """Terminal states return themselves and don't raise."""
        for terminal in CallStateMachine.TERMINAL_STATES:
            result = self.sm.transition(terminal, "customer-ended-call")
            assert result == terminal

    def test_all_terminal_states_recognized(self):
        """Verify the set of terminal states."""
        assert CallStateMachine.TERMINAL_STATES == {
            "ended",
            "failed",
            "canceled",
            "no_answer",
        }
