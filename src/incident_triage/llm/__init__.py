"""Pluggable LLM providers."""
from __future__ import annotations

import os

from incident_triage.llm.base import LLMError, LLMProvider


def get_provider(name: str | None = None) -> LLMProvider:
    name = (name or os.getenv("LLM_PROVIDER", "anthropic")).lower()
    if name == "anthropic":
        from incident_triage.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "google":
        from incident_triage.llm.google_provider import GoogleProvider
        return GoogleProvider()
    if name == "fake":
        from incident_triage.llm.fake_provider import FakeProvider
        return FakeProvider()
    raise ValueError(f"unknown LLM provider {name!r}")


__all__ = ["LLMError", "LLMProvider", "get_provider"]