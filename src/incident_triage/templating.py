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
_SECRETS = [
    # "Authorization: Bearer abc", "Authorization: Basic abc"
    (re.compile(r"(?i)\b(authorization\s*[:=]\s*(?:bearer|basic|token|apikey)\s+)[^\s,;\"']+"), r"\1<SECRET>"),
    # A bare "Bearer abc123..." (must contain a digit, so "bearer authentication" is left alone)
    (re.compile(r"(?i)\b(bearer\s+)(?=[\w.~+/=-]*\d)[\w.~+/=-]{8,}"), r"\1<SECRET>"),
    # JSON Web Tokens
    (re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]*"), "<SECRET>"),
    # AWS access key ids
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "<SECRET>"),
    # API keys with a recognisable prefix (sk-..., GitHub, Google)
    (re.compile(r"\b(?:sk-[\w-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AIza[\w-]{30,})"), "<SECRET>"),
    # password=..., token: ..., and JSON style "password": "..." (key and value may be quoted)
    (re.compile(r"""(?i)(["']?\b(?:password|passwd|pwd|token|secret|api[_-]?key)["']?\s*[=:]\s*)"""
                r"""(?:"[^"]*"|'[^']*'|\S+)"""), r"\1<SECRET>"),
]
_EMAIL  = (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL>")
_UUID   = (re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                      r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?![0-9a-fA-F])"), "<UUID>")
_IP     = (re.compile(r"/?\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<IP>")
_BLOCK  = (re.compile(r"\bblk_-?\d+\b"), "<BLK>")
_PATH   = (re.compile(r"(?:/[\w.\-]+){2,}"), "<PATH>")
_HEX    = (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>")
# A number, optionally followed by a unit that is kept ("3.5s" -> "<NUM>s").
# "(?!\.\d)" stops "3.5x" from being half-replaced as "<NUM>.5x".
_NUM    = (re.compile(r"\b-?\d+(?:\.\d+|(?!\.\d))"
                      r"(?=(?:ns|us|µs|ms|s|secs?|m|mins?|h|hrs?|d|[KMGT]i?[Bb]|B)?\b)"), "<NUM>")
_SPACES = re.compile(r"\s+")

# Secrets are in both lists: templates are sent to the LLM too.
TEMPLATE_RULES = [*_SECRETS, _EMAIL, _UUID, _IP, _BLOCK, _PATH, _HEX, _NUM]
MASK_RULES = [*_SECRETS, _EMAIL, _IP]


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