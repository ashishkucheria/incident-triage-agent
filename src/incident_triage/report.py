"""Stage 5: render the validated TriageReport as a Markdown incident report.

Pure function: takes data, returns a string. No file writing, no LLM calls,
so it is trivial to test. cli.py decides where the text goes.
"""
from __future__ import annotations

from datetime import datetime

from incident_triage.cluster import Score
from incident_triage.ingest import ParseStats
from incident_triage.models import Cluster, TriageReport


def _cell(text: str) -> str:
    """Make text safe inside a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def _fmt(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def render(report: TriageReport,
           ranked: list[tuple[Cluster, Score]],
           source: str = "",
           provider: str = "",
           stats: ParseStats | None = None) -> str:
    by_id = {c.id: (c, s) for c, s in ranked}
    evidence = [by_id[cid] for cid in report.evidence if cid in by_id]
    all_events = [e for c, _ in ranked for e in c.events]
    start = min((e.timestamp for e in all_events), default=None)
    end = max((e.timestamp for e in all_events), default=None)

    out: list[str] = []
    w = out.append

    # --- Header -----------------------------------------------------------
    w("# Incident Report (AI-generated draft)\n")
    w("> Generated automatically from logs. Verify before acting or sharing.\n")
    w(f"- **Source:** `{source or 'unknown'}`")
    if start and end:
        w(f"- **Log window:** {_fmt(start)} to {_fmt(end)}")
    if stats:
        w(f"- **Lines:** {stats.total} read, {stats.parsed} parsed, {stats.unparsed} unparsed")
    w(f"- **Clusters:** {len(ranked)}")
    if provider:
        w(f"- **Analysed by:** {provider}")
    w(f"- **Model confidence:** {report.model_confidence.value} (the model's self-rating, not a probability)")
    w(f"- **Generated:** {_fmt(datetime.now())}\n")

    # --- Summary ----------------------------------------------------------
    w("## Summary\n")
    w(report.summary + "\n")
    w("## Probable root cause\n")
    w(report.probable_root_cause + "\n")

    # --- Evidence ---------------------------------------------------------
    w("## Evidence\n")
    w("| Cluster | Pattern | Count | Level | First seen | Last seen | Score |")
    w("|---|---|---|---|---|---|---|")
    for c, s in evidence:
        w(f"| `{c.id}` | {_cell(c.template)} | {c.count} | {c.max_level.name} "
          f"| {_fmt(c.first_seen)} | {_fmt(c.last_seen)} | {s.total:.2f} |")
    w("")
    for c, _ in evidence:
        w(f"<details><summary>Sample lines for <code>{c.id}</code></summary>\n")
        w("```")
        w("\n".join(c.samples))
        w("```\n</details>\n")

    # --- Remediation ------------------------------------------------------
    w("## Suggested next steps\n")
    for step in report.remediation:
        w(f"- [ ] {step}")
    w("")

    # --- Postmortem draft -------------------------------------------------
    w("## Postmortem draft\n")
    w("### Timeline\n")
    w("| Time | Event |")
    w("|---|---|")
    timeline = sorted(
        [(c.first_seen, f"First `{c.id}`: {_cell(c.template)}") for c, _ in evidence]
        + [(c.last_seen, f"Last `{c.id}` ({c.count} total)") for c, _ in evidence]
    )
    for ts, text in timeline:
        w(f"| {_fmt(ts)} | {text} |")
    w("")
    w("### Impact\n")
    w("_To be filled in by the on-call engineer: affected users, services, duration._\n")
    w("### Root cause\n")
    w(f"{report.probable_root_cause} _(AI hypothesis, confirm before closing)_\n")
    w("### Action items\n")
    w("| Action | Owner | Due |")
    w("|---|---|---|")
    for step in report.remediation:
        w(f"| {_cell(step)} | _TBD_ | _TBD_ |")
    w("")

    # --- Other clusters ---------------------------------------------------
    others = [(c, s) for c, s in ranked if c.id not in report.evidence][:5]
    if others:
        w("## Other top clusters (not cited)\n")
        w("| Cluster | Pattern | Count | Score |")
        w("|---|---|---|---|")
        for c, s in others:
            w(f"| `{c.id}` | {_cell(c.template)} | {c.count} | {s.total:.2f} |")
        w("")

    return "\n".join(out)