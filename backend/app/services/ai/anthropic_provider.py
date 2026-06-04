"""Anthropic implementation of the AI provider — the production backend.

The Messages API has no JSON *mode*, but it has something stronger: **forced
tool use**. We expose a single tool whose ``input_schema`` is the
:class:`DualSignalDraft` JSON schema and force the model to call it
(``tool_choice`` = that tool), so the reply comes back as a structured object
the API itself validated against the schema — an unparseable signal becomes
near-impossible. The tool input is serialised back to JSON text so the base
class's existing extraction + Pydantic validation still runs unchanged (defence
in depth). If a response somehow carries no tool block, we fall back to the
base's tolerant text extraction. The system prompt is passed via the dedicated
``system`` parameter, as the API requires.
"""

from __future__ import annotations

import json
from typing import Any, Final

import anthropic

from app.services.ai.base import (
    AIRequestError,
    AIResponseError,
    BaseAIProvider,
    CompletionResult,
    DualSignalDraft,
    TokenUsage,
)

# The single tool the model is forced to call. Its schema is the dual-signal
# contract, so the provider validates structure before we ever see the reply.
_SIGNAL_TOOL_NAME: Final[str] = "emit_dual_signal"


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

    @staticmethod
    def _signal_tool() -> dict[str, Any]:
        """The forced tool definition: name + the dual-signal JSON schema."""
        return {
            "name": _SIGNAL_TOOL_NAME,
            "description": (
                "Emit the scalp and swing trade signals for the instrument as "
                "structured data. Both signals are mandatory and directional."
            ),
            "input_schema": DualSignalDraft.model_json_schema(),
        }

    async def _complete(self, *, system: str, user: str) -> CompletionResult:
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[self._signal_tool()],
                tool_choice={"type": "tool", "name": _SIGNAL_TOOL_NAME},
            )
        except anthropic.AnthropicError as exc:
            raise AIRequestError(f"Anthropic request failed: {exc}") from exc

        return CompletionResult(
            text=self._extract_payload(response), usage=self._usage_of(response)
        )

    @classmethod
    def _extract_payload(cls, response: anthropic.types.Message) -> str:
        """Return JSON text from the forced tool call, falling back to text.

        The happy path is a ``tool_use`` block whose ``input`` is the structured
        object — serialised back to JSON so the base parser validates it like any
        other reply. If no tool block is present (an unusual response), fall back
        to concatenating text blocks so a model that answered in prose still has a
        chance of parsing.
        """
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == (
                _SIGNAL_TOOL_NAME
            ):
                return json.dumps(getattr(block, "input", {}))
        return cls._extract_text(response)

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        """Concatenate the text blocks of a Messages response.

        A response is a list of content blocks; non-text blocks are skipped.
        An empty result surfaces as an :class:`AIResponseError` so it
        is handled on the same path as other malformed replies.
        """
        parts = [
            getattr(block, "text", "")
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        text = "".join(parts).strip()
        if not text:
            raise AIResponseError("Anthropic response contained no usable content")
        return text

    @staticmethod
    def _usage_of(response: object) -> TokenUsage | None:
        """Read token counts from a Messages ``usage`` block, if present.

        Anthropic names them ``input_tokens``/``output_tokens``; map them onto the
        provider-neutral :class:`TokenUsage`. Tolerant: a response (or test fake)
        without usage yields ``None`` rather than raising.
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        return TokenUsage(
            prompt_tokens=getattr(usage, "input_tokens", None),
            completion_tokens=getattr(usage, "output_tokens", None),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()
