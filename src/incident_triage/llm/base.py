"""The interface every LLM backend implements."""
from __future__ import annotations

from typing import Protocol


class LLMError(Exception):
    """Any provider failure: network, rate limit, refusal, truncated answer."""


class LLMProvider(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str:
        """Send one prompt, return the model's text answer. Raise LLMError on failure."""
        ...