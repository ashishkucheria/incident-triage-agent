"""Stage 2: turn log messages into templates, and mask sensitive values.

Two jobs:
- template(): replace every variable part, so lines that differ only by IDs,
  numbers or IPs become the same string. Used for grouping.
- mask(): replace only sensitive values (IPs, emails, secrets), keeping the
  rest readable. Used for the sample lines that are sent to the LLM.
"""
from __future__ import annotations

import re

# Order matters: specific patterns first, generic numbers last.
# Otherwise "blk_123" would become "blk_<NUM>" and "10.0.0.1" would become "<NUM>.<NUM>...".
_SECRET = (re.compile(r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)\s*[=:]\s*\S+"), r"\1=<SECRET>")
_EMAIL  = (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL>")
_IP     = (re.compile(r"/?\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<IP>")
_BLOCK  = (re.compile(r"\bblk_-?\d+\b"), "<BLK>")
_PATH   = (re.compile(r"(?:/[\w.\-]+){2,}"), "<PATH>")
_HEX    = (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>")
_NUM    = (re.compile(r"\b-?\d+(?:\.\d+)?\b"), "<NUM>")
_SPACES = re.compile(r"\s+")

TEMPLATE_RULES = [_SECRET, _EMAIL, _IP, _BLOCK, _PATH, _HEX, _NUM]
MASK_RULES = [_SECRET, _EMAIL, _IP]


def _apply(text: str, rules: list[tuple[re.Pattern[str], str]]) -> str:
    for pattern, replacement in rules:
        text = pattern.sub(replacement, text)
    return _SPACES.sub(" ", text).strip()


def template(message: str) -> str:
    """Replace every variable part. Similar lines give the same result."""
    return _apply(message, TEMPLATE_RULES)


def mask(text: str) -> str:
    """Replace only sensitive values. Safe to send outside the machine."""
    return _apply(text, MASK_RULES)