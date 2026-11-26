"""Gemini implementation of the provider interface."""
from __future__ import annotations

import os

from google import genai
from google.genai import errors, types

from incident_triage.llm.base import LLMError


class GoogleProvider:
    name = "google"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        # Reads GEMINI_API_KEY (or GOOGLE_API_KEY) from the environment.
        try:
            self.client = genai.Client()
        except ValueError as e:           # raised when no API key is set
            raise LLMError(f"could not set up Gemini (is GEMINI_API_KEY set?): {e}") from e

    def complete(self, system: str, user: str) -> str:
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",  # ask Gemini for JSON only
                ),
            )
        except errors.ClientError as e:   # 4xx: bad key, bad model name, rate limit
            raise LLMError(f"Gemini client error {e.code}: {e.message}") from e
        except errors.ServerError as e:   # 5xx
            raise LLMError(f"Gemini server error {e.code}") from e

        if not resp.text:                 # blocked by safety filters, or empty
            reason = resp.candidates[0].finish_reason if resp.candidates else "no candidates"
            raise LLMError(f"Gemini returned no text ({reason})")
        return resp.text