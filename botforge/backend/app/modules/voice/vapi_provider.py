"""Vapi voice provider — concrete implementation of VoiceProvider protocol.

Uses the vapi-server-sdk (AsyncVapi) to manage assistants and validate API keys.
"""

import structlog
from vapi import AsyncVapi
from vapi.types import Server

logger = structlog.get_logger()


class VapiProvider:
    """Vapi voice provider implementation."""

    def __init__(self, private_key: str) -> None:
        self._client = AsyncVapi(token=private_key)

    async def create_assistant(
        self,
        name: str,
        first_message: str,
        system_prompt: str | None = None,
        webhook_url: str | None = None,
    ) -> dict:
        """Create a Vapi assistant for a workspace.

        Returns dict with 'id' and other assistant metadata.
        """
        kwargs: dict = {
            "name": name,
            "first_message": first_message,
        }

        if system_prompt:
            # Set model with system prompt
            kwargs["model"] = {
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": system_prompt}],
            }

        if webhook_url:
            kwargs["server"] = Server(url=webhook_url)
            kwargs["server_messages"] = ["status-update", "end-of-call-report"]

        assistant = await self._client.assistants.create(**kwargs)

        logger.info(
            "vapi.assistant_created",
            assistant_id=assistant.id,
            name=name,
        )

        return {
            "id": assistant.id,
            "name": assistant.name,
            "created_at": str(assistant.created_at) if hasattr(assistant, "created_at") else None,
        }

    async def validate_keys(self) -> bool:
        """Validate Vapi API keys by listing assistants (limit=1)."""
        try:
            await self._client.assistants.list(limit=1)
            return True
        except Exception as e:
            logger.warning("vapi.key_validation_failed", error=str(e))
            return False

    async def delete_assistant(self, assistant_id: str) -> None:
        """Delete a Vapi assistant."""
        try:
            await self._client.assistants.delete(id=assistant_id)
            logger.info("vapi.assistant_deleted", assistant_id=assistant_id)
        except Exception as e:
            logger.warning(
                "vapi.assistant_delete_failed",
                assistant_id=assistant_id,
                error=str(e),
            )

    async def get_assistant(self, assistant_id: str) -> dict | None:
        """Get Vapi assistant details."""
        try:
            assistant = await self._client.assistants.get(id=assistant_id)
            return {
                "id": assistant.id,
                "name": assistant.name,
            }
        except Exception:
            return None
