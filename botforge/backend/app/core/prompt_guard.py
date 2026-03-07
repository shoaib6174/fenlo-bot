"""
Prompt injection guard with multi-layer defense.

Implements three layers of protection:
1. Heuristic detection: regex patterns for known injection phrases
2. Input sandwiching: wrap user message in delimiters
3. Output validation: check response doesn't leak system prompt
"""

import re
from dataclasses import dataclass

import structlog

from app.core.engine import MessageContext

logger = structlog.get_logger()


@dataclass
class PromptGuardConfig:
    """Configuration for prompt guard behavior."""

    enabled: bool = True
    log_attempts: bool = True
    block_on_detection: bool = True
    safe_response: str = "I'm here to help with your questions. How can I assist you today?"


class PromptGuard:
    """
    Multi-layer prompt injection defense.

    Layer 1: Pattern-based detection
    Layer 2: Input sandwiching with delimiters
    Layer 3: Output validation (checks response doesn't leak system prompt)
    """

    # Known injection patterns (case-insensitive)
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior|above|earlier|the\s+above)\s*(instructions?|prompts?|commands?|rules?)?",
        r"(reveal|show|print|display|tell\s+me|give\s+me)\s+(\w+\s+)?(the\s+)?(system|original|initial)\s+(prompt|instructions?)",
        r"you\s+are\s+now\s+",
        r"disregard\s+(all\s+)?(previous|prior|earlier)\s+(instructions?|prompts?)",
        r"pretend\s+(you\s+are|to\s+be)\s+",
        r"(act|behave)\s+(as|like)\s+",
        r"forget\s+(all\s+)?(previous|prior|earlier|your)\s*(instructions?|prompts?|training)?",
        r"new\s+(instructions?|rules?|commands?):",
        r"system\s+message:",
        r"</?\s*system\s*>",  # Trying to close system tags
        r"<\s*user_message\s*>",  # Trying to inject our own delimiters
    ]

    def __init__(self, config: PromptGuardConfig | None = None):
        """
        Initialize prompt guard.

        Args:
            config: Optional configuration, uses defaults if not provided
        """
        self.config = config or PromptGuardConfig()
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.INJECTION_PATTERNS
        ]

    def check(self, message: str) -> tuple[bool, str | None]:
        """
        Check if message contains injection attempt.

        Args:
            message: User message to check

        Returns:
            Tuple of (is_safe, matched_pattern)
            - is_safe: True if message is safe, False if injection detected
            - matched_pattern: The pattern that matched, or None if safe
        """
        if not self.config.enabled:
            return True, None

        for pattern in self.compiled_patterns:
            match = pattern.search(message)
            if match:
                return False, pattern.pattern

        return True, None

    def sandwich(self, user_message: str) -> str:
        """
        Wrap user input in delimiters for LLM context.

        This helps the LLM distinguish user input from system instructions.

        Args:
            user_message: Raw user message

        Returns:
            Sandwiched message with delimiters
        """
        return f"""<user_message>
{user_message}
</user_message>"""

    def validate_output(self, response: str, system_prompt: str | None = None) -> bool:
        """
        Validate that LLM response doesn't leak system prompt.

        Args:
            response: LLM-generated response
            system_prompt: Optional system prompt to check against

        Returns:
            True if response is safe, False if it appears to leak system prompt
        """
        if not system_prompt:
            return True

        # Check if response contains significant chunks of system prompt
        # Use a sliding window approach to detect leaked segments
        WINDOW_SIZE = 50  # Check for 50-character chunks
        MIN_LEAK_LENGTH = 40  # Consider it a leak if 40+ chars match

        if len(system_prompt) < WINDOW_SIZE:
            # For short prompts, be more lenient - only flag if it appears verbatim
            # (not as part of a natural sentence)
            # Check for the prompt surrounded by word boundaries or quotes
            import re

            pattern = r'["\']' + re.escape(system_prompt) + r'["\']'
            if re.search(pattern, response, re.IGNORECASE):
                return False
            # Also check if it appears verbatim at start of sentence
            pattern = r"(^|\. )" + re.escape(system_prompt) + r"($|\.|\,)"
            if re.search(pattern, response, re.IGNORECASE):
                return False
            return True

        # For longer prompts, check sliding windows
        for i in range(len(system_prompt) - WINDOW_SIZE + 1):
            chunk = system_prompt[i : i + WINDOW_SIZE].lower()
            if chunk in response.lower():
                # Found a matching chunk, check how much matches
                match_length = WINDOW_SIZE
                # Try to extend the match
                j = i + WINDOW_SIZE
                while j < len(system_prompt) and system_prompt[j].lower() in response.lower():
                    match_length += 1
                    j += 1

                if match_length >= MIN_LEAK_LENGTH:
                    return False

        return True


class PromptGuardStep:
    """
    Pipeline step that guards against prompt injection.

    This step:
    1. Checks for injection patterns
    2. Sandwiches user input in delimiters
    3. Logs injection attempts
    4. Optionally halts pipeline and returns safe response
    """

    def __init__(self, guard: PromptGuard | None = None):
        """
        Initialize guard step.

        Args:
            guard: Optional PromptGuard instance, creates default if not provided
        """
        self.guard = guard or PromptGuard()

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        Execute prompt injection guard.

        Args:
            context: Current message context

        Returns:
            Updated context (possibly halted if injection detected)
        """
        # Check for injection
        is_safe, matched_pattern = self.guard.check(context.message)

        if not is_safe:
            # Log the attempt
            if self.guard.config.log_attempts:
                logger.warning(
                    "prompt_injection_detected",
                    workspace_id=str(context.workspace_id),
                    user_id=str(context.user_id) if context.user_id else None,
                    pattern=matched_pattern,
                    message_preview=context.message[:100],
                )

            # Block if configured to do so
            if self.guard.config.block_on_detection:
                context.should_halt = True
                context.halt_reason = "prompt_injection_detected"
                context.response = self.guard.config.safe_response
                context.metadata["injection_blocked"] = True
                context.metadata["matched_pattern"] = matched_pattern

                return context

        # Sandwich the message (always do this, even if no injection detected)
        # This is a preventive measure
        context.metadata["original_message"] = context.message
        context.message = self.guard.sandwich(context.message)
        context.metadata["sandwiched"] = True

        return context
