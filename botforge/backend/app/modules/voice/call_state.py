"""Call state machine for voice call lifecycle management.

Maps Vapi webhook events to call states with validated transitions.

States: initiated, ringing, connected, ended, failed, canceled, no_answer
Terminal states: ended, failed, canceled, no_answer
"""

import structlog

logger = structlog.get_logger()


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, current_state: str, target_state: str):
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(f"Invalid transition: {current_state} → {target_state}")


class CallStateMachine:
    """Manages call state transitions based on Vapi webhook events.

    Valid transitions:
        initiated  → ringing, failed
        ringing    → connected, no_answer, failed, canceled
        connected  → ended, failed

    Terminal states ignore further events (idempotent).
    """

    VALID_TRANSITIONS: dict[str, set[str]] = {
        "initiated": {"ringing", "failed"},
        "ringing": {"connected", "no_answer", "failed", "canceled"},
        "connected": {"ended", "failed"},
    }

    TERMINAL_STATES: set[str] = {"ended", "failed", "canceled", "no_answer"}

    # Vapi status/event values → our internal states
    _EVENT_STATE_MAP: dict[str, str] = {
        # status-update statuses
        "queued": "ringing",
        "ringing": "ringing",
        "in-progress": "connected",
        # end-of-call-report is always → ended (unless error)
        "end-of-call-report": "ended",
        # endedReason values that map to specific states
        "customer-did-not-answer": "no_answer",
        "assistant-did-not-answer": "no_answer",
        "twilio-failed-to-connect-call": "failed",
        "pipeline-error-openai-llm-failed": "failed",
        "pipeline-error-deepgram-transcriber-failed": "failed",
        "pipeline-error-vapi-llm-failed": "failed",
        "pipeline-error-eleven-labs-voice-failed": "failed",
        "silence-timed-out": "ended",
        "exceeded-max-duration": "ended",
        "manually-canceled": "canceled",
        "phone-call-provider-closed-websocket": "ended",
        "customer-ended-call": "ended",
        "assistant-ended-call": "ended",
        "assistant-forwarded-call": "ended",
        "voicemail": "ended",
    }

    def transition(self, current_state: str, event: str) -> str:
        """Compute new state from current state and Vapi event.

        Args:
            current_state: Current call state.
            event: Vapi event string (status or endedReason).

        Returns:
            New state string.

        Raises:
            InvalidTransitionError: If transition is not allowed and
                current state is not terminal.
        """
        new_state = self._map_event_to_state(event)

        # Terminal states ignore further events
        if current_state in self.TERMINAL_STATES:
            logger.info(
                "call_state.terminal_ignored",
                current=current_state,
                vapi_event=event,
                target=new_state,
            )
            return current_state

        # Validate transition
        allowed = self.VALID_TRANSITIONS.get(current_state, set())
        if new_state not in allowed:
            raise InvalidTransitionError(current_state, new_state)

        logger.info(
            "call_state.transition",
            current=current_state,
            vapi_event=event,
            new_state=new_state,
        )
        return new_state

    def _map_event_to_state(self, event: str) -> str:
        """Map a Vapi event or status string to an internal state.

        Falls back to 'failed' for unrecognized events.
        """
        state = self._EVENT_STATE_MAP.get(event)
        if state is None:
            # Unrecognized event — treat as failure
            logger.warning("call_state.unknown_event", event=event)
            return "failed"
        return state
