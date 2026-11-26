"""Stage 3: group events by template, then rank the groups.

Ranking decides what the LLM sees, so it is the most important step.
Every score is broken into parts so a human can see WHY a cluster ranked high.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from incident_triage.models import Cluster, Level, LogEvent
from incident_triage.templating import mask, template

ERROR_WORDS = re.compile(
    r"(?i)\b(exception|error|fail\w*|timeout|timed out|refused|denied|"
    r"corrupt\w*|unreachable|lost|abort\w*|killed|crash\w*)\b"
)

# Hand-picked starting weights; evals decide whether they change.
WEIGHTS = {"severity": 0.40, "keywords": 0.35, "rarity": 0.25}


def cluster_id(tmpl: str) -> str:
    """Stable short id: the same template gets the same id in every run."""
    return hashlib.sha1(tmpl.encode()).hexdigest()[:8]


def build_clusters(events: list[LogEvent], max_samples: int = 3) -> list[Cluster]:
    """Put each event in the cluster for its template."""
    groups: dict[str, Cluster] = {}
    for event in events:
        tmpl = template(event.message)
        cluster = groups.get(tmpl)
        if cluster is None:
            cluster = Cluster(id=cluster_id(tmpl), template=tmpl)
            groups[tmpl] = cluster
        cluster.events.append(event)
        if len(cluster.samples) < max_samples:
            cluster.samples.append(mask(event.raw))
    return list(groups.values())


@dataclass(frozen=True)
class Score:
    """A cluster's rank score and the parts it is made of."""
    severity: float
    keywords: float
    rarity: float

    @property
    def total(self) -> float:
        return (WEIGHTS["severity"] * self.severity
                + WEIGHTS["keywords"] * self.keywords
                + WEIGHTS["rarity"] * self.rarity)


def score(cluster: Cluster, total_events: int) -> Score:
    level = cluster.max_level
    severity = 1.0 if level in (Level.ERROR, Level.FATAL) else 0.6 if level == Level.WARN else 0.0
    keywords = 1.0 if ERROR_WORDS.search(cluster.template) else 0.0
    # Log scale: 1 line out of 2000 -> 1.0, all 2000 lines -> 0.0.
    rarity = 1.0 - math.log(cluster.count) / math.log(total_events) if total_events > 1 else 0.0
    return Score(severity, keywords, rarity)


def rank(clusters: list[Cluster]) -> list[tuple[Cluster, Score]]:
    """Highest score first; ties go to the smaller (rarer) cluster."""
    total = sum(c.count for c in clusters)
    scored = [(c, score(c, total)) for c in clusters]
    scored.sort(key=lambda cs: (-cs[1].total, cs[0].count))
    return scored