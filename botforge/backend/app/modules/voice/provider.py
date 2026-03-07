"""VoiceProvider protocol — vendor-agnostic interface for voice services.

Follows the same pattern as RAGPipeline protocol in app/modules/rag/pipeline.py.
"""

from typing import Protocol


class VoiceProvider(Protocol):
    """Protocol for voice provider operations — vendor-agnostic interface."""

    async def create_assistant(
        self,
        name: str,
        first_message: str,
        system_prompt: str | None = None,
        webhook_url: str | None = None,
    ) -> dict:
        """Create a voice assistant.

        Args:
            name: Assistant name (typically workspace name)
            first_message: First message the assistant speaks
            system_prompt: Optional system prompt for the assistant
            webhook_url: URL for webhook events

        Returns:
            Dict with at least 'id' key (provider's assistant ID)
        """
        ...

    async def validate_keys(self) -> bool:
        """Validate that configured API keys are valid.

        Returns:
            True if keys are valid, False otherwise
        """
        ...

    async def delete_assistant(self, assistant_id: str) -> None:
        """Delete a voice assistant.

        Args:
            assistant_id: Provider's assistant ID
        """
        ...

    async def get_assistant(self, assistant_id: str) -> dict | None:
        """Get assistant details.

        Args:
            assistant_id: Provider's assistant ID

        Returns:
            Assistant details dict or None if not found
        """
        ...
