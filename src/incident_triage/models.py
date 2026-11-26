"""Data types shared by every stage of the pipeline.

Each stage takes and returns these types, so stages never depend on each
other's internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Level(Enum):
    """Log severity, ordered so levels can be compared (ERROR > WARN)."""
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50
    UNKNOWN = 0

    @classmethod
    def parse(cls, text: str) -> Level:
        """Map a raw level string to a Level. Unrecognised text gives UNKNOWN."""
        aliases = {"WARNING": "WARN", "SEVERE": "ERROR", "CRITICAL": "FATAL"}
        name = aliases.get(text.upper(), text.upper())
        return cls.__members__.get(name, cls.UNKNOWN)


@dataclass(frozen=True)
class LogEvent:
    """One parsed log line (stage 1 output)."""
    timestamp: datetime
    level: Level
    component: str
    message: str
    raw: str
    keys: dict[str, str] = field(default_factory=dict)  # format-specific, e.g. {"block_id": "blk_123"}
    label: str | None = None  # ground-truth label when the dataset has one (BGL)


@dataclass
class Cluster:
    """Events that share one template (stage 3 output)."""
    id: str
    template: str
    events: list[LogEvent] = field(default_factory=list)
    samples: list[str] = field(default_factory=list)  # masked lines, safe to send to an LLM

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def first_seen(self) -> datetime:
        return min(e.timestamp for e in self.events)

    @property
    def last_seen(self) -> datetime:
        return max(e.timestamp for e in self.events)

    @property
    def max_level(self) -> Level:
        return max((e.level for e in self.events), key=lambda lv: lv.value)


class Confidence(Enum):
    """The model's self-rating. Not a probability."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class TriageReport:
    """Validated LLM answer (stage 4 output)."""
    summary: str
    probable_root_cause: str
    model_confidence: Confidence
    evidence: list[str]  # cluster ids; must all exist
    remediation: list[str]