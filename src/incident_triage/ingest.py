"""Stage 1: parse raw log lines into LogEvent objects.

One parser per log format, all behind the same small interface, so adding a
format (e.g. BGL) means adding one class, not rewriting this file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Protocol

from incident_triage.models import Level, LogEvent


class LogParser(Protocol):
    """Anything with a parse_line method counts as a parser."""
    def parse_line(self, line: str) -> LogEvent | None:
        """Return a LogEvent, or None if the line does not match this format."""
        ...


class HdfsParser:
    """HDFS format: date time pid level component: message"""

    LINE = re.compile(
        r"^(?P<date>\d{6})\s+(?P<time>\d{6})\s+(?P<pid>\d+)\s+"
        r"(?P<level>[A-Z]+)\s+(?P<component>[^:]+):\s+(?P<message>.*)$"
    )
    BLOCK_ID = re.compile(r"blk_-?\d+")

    def parse_line(self, line: str) -> LogEvent | None:
        m = self.LINE.match(line)
        if not m:
            return None
        try:
            ts = datetime.strptime(m["date"] + m["time"], "%y%m%d%H%M%S")
        except ValueError:
            return None
        keys = {"pid": m["pid"]}
        block = self.BLOCK_ID.search(m["message"])
        if block:
            keys["block_id"] = block.group()
        return LogEvent(
            timestamp=ts,
            level=Level.parse(m["level"]),
            component=m["component"].strip(),
            message=m["message"].strip(),
            raw=line,
            keys=keys,
        )


PARSERS: dict[str, LogParser] = {
    "hdfs": HdfsParser(),
}


@dataclass
class ParseStats:
    """How much of the file was understood. Unparsed lines are counted, never hidden."""
    total: int = 0
    parsed: int = 0
    unparsed_samples: list[str] = field(default_factory=list)

    @property
    def unparsed(self) -> int:
        return self.total - self.parsed


def iter_events(path: Path, fmt: str, stats: ParseStats) -> Iterator[LogEvent]:
    """Yield events one at a time, so a huge file never has to fit in memory."""
    parser = PARSERS.get(fmt)
    if parser is None:
        raise ValueError(f"unknown format {fmt!r}; known: {sorted(PARSERS)}")
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            stats.total += 1
            event = parser.parse_line(line)
            if event is None:
                if len(stats.unparsed_samples) < 5:
                    stats.unparsed_samples.append(line)
                continue
            stats.parsed += 1
            yield event


def load(path: str | Path, fmt: str = "hdfs") -> tuple[list[LogEvent], ParseStats]:
    """Read a whole file. Fine for v1 sample files; use iter_events for big ones."""
    stats = ParseStats()
    events = list(iter_events(Path(path), fmt, stats))
    return events, stats