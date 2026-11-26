"""Claude implementation (default provider)."""
from __future__ import annotations

import os

import anthropic

from incident_triage.llm.base import LLMError


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("LLM_MODEL", "claude-opus-5-5")
        # Reads ANTHROPIC_API_KEY from the environment; SDK retries 429/5xx itself.
        try:
            self.client = anthropic.Anthropic(max_retries=3, timeout=120)
        except anthropic.AnthropicError as e:
            raise LLMError(f"could not set up the Anthropic client: {e}") from e
        # The SDK only notices missing credentials at request time, as a TypeError.
        # getattr: older SDKs lack auth_token/credentials, and must still give this message.
        if not (self.client.api_key or getattr(self.client, "auth_token", None)
                or getattr(self.client, "credentials", None)):
            raise LLMError("no Anthropic credentials: set ANTHROPIC_API_KEY in .env")

    def complete(self, system: str, user: str) -> str:
        try:
            resp = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": user}],
                # If Claude declines on safety grounds, the API retries on a fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise LLMError("invalid or missing ANTHROPIC_API_KEY") from e
        except anthropic.RateLimitError as e:
            raise LLMError("rate limited, retries exhausted") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("network error") from e

        if resp.stop_reason == "refusal":
            raise LLMError("model declined the request")
        if resp.stop_reason == "max_tokens":
            raise LLMError("answer was cut off (max_tokens)")
        return "".join(b.text for b in resp.content if b.type == "text")