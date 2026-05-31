"""Anthropic implementation of the AI provider — the production backend.

The Messages API has no dedicated JSON mode, so correctness rests on the base
class's prompt (which mandates strict JSON) plus its tolerant extraction
(which copes with the occasional wrapping prose). The system prompt is passed
via the dedicated ``system`` parameter rather than a system *message*, as the
API requires.
"""

from __future__ import annotations

import anthropic

from app.services.ai.base import AIRequestError, AIResponseError, BaseAIProvider


class AnthropicProvider(BaseAIProvider):
    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout_seconds: float = 30.0,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self.model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._owns_client = client is None
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)

    async def _complete(self, *, system: str, user: str) -> str:
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.AnthropicError as exc:
            raise AIRequestError(f"Anthropic request failed: {exc}") from exc

        return self._extract_text(response)

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        """Concatenate the text blocks of a Messages response.

        A response is a list of content blocks; non-text blocks are skipped.
        An empty result surfaces as an :class:`AIResponseError` so it
        is handled on the same path as other malformed replies.
        """
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "".join(parts).strip()
        if not text:
            raise AIResponseError("Anthropic response contained no text content")
        return text

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()
