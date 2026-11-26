"""Returns a canned answer, so tests run offline and free."""
from __future__ import annotations


class FakeProvider:
    name = "fake"

    def __init__(self, answer: str = "") -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []  # lets tests inspect the prompt that was sent

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.answer