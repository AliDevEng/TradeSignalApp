"""Groq implementation of the AI provider — the development/default backend.

Groq's API is OpenAI-shaped, so we can ask for guaranteed-JSON output via
``response_format={"type": "json_object"}``. That doesn't remove the need for
the base class's defensive parsing (the model can still return well-formed
JSON with the wrong keys), but it makes a clean parse the overwhelming case.
"""

from __future__ import annotations

import groq

from app.services.ai.base import AIRequestError, BaseAIProvider


class GroqProvider(BaseAIProvider):
    provider_name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout_seconds: float = 30.0,
        client: groq.AsyncGroq | None = None,
    ) -> None:
        self.model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._owns_client = client is None
        # The SDK retries network blips internally; we add our own typed error
        # boundary on top so callers never see a raw ``groq.*`` exception.
        self._client = client or groq.AsyncGroq(api_key=api_key, timeout=timeout_seconds)

    async def _complete(self, *, system: str, user: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except groq.GroqError as exc:
            raise AIRequestError(f"Groq request failed: {exc}") from exc

        content = response.choices[0].message.content if response.choices else None
        return content or ""

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()
