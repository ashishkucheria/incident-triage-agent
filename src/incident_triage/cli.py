"""Command-line entry point: triage <logfile>.

Wires stages 1-5 together. This is the only file that touches the outside
world: arguments, environment, files, exit codes. Every other module stays pure.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from incident_triage.cluster import build_clusters, rank
from incident_triage.ingest import PARSERS, load
from incident_triage.llm import LLMError, get_provider
from incident_triage.report import render
from incident_triage.triage import TriageError, triage

EXIT_OK, EXIT_USAGE, EXIT_LLM = 0, 2, 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="triage",
        description="Group log lines into patterns and draft an incident report with an LLM.",
    )
    p.add_argument("logfile", type=Path, help="path to the log file")
    p.add_argument("--format", default="hdfs", choices=sorted(PARSERS), help="log format (default: hdfs)")
    p.add_argument("--provider", help="anthropic | google | fake (default: LLM_PROVIDER env, else anthropic)")
    p.add_argument("--top", type=int, default=5, help="clusters sent to the LLM (default: 5)")
    p.add_argument("--out", type=Path, default=Path("reports"), help="folder for the report (default: reports/)")
    p.add_argument("--no-llm", action="store_true", help="only show ranked clusters; no LLM call, no cost")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # reads .env in the current folder; real env vars win over the file
    args = parse_args(argv)

    if not args.logfile.is_file():
        print(f"error: log file not found: {args.logfile}", file=sys.stderr)
        return EXIT_USAGE

    # Stages 1-3: deterministic, free
    events, stats = load(args.logfile, args.format)
    print(f"Parsed {stats.parsed}/{stats.total} lines", file=sys.stderr)
    if stats.unparsed:
        print(f"warning: {stats.unparsed} lines did not match the {args.format} format, e.g.:", file=sys.stderr)
        for line in stats.unparsed_samples:
            print(f"  {line[:120]}", file=sys.stderr)
    if not events:
        print("error: no lines could be parsed; is --format right?", file=sys.stderr)
        return EXIT_USAGE

    ranked = rank(build_clusters(events))
    print(f"{len(ranked)} clusters; top {min(args.top, len(ranked))}:", file=sys.stderr)
    for c, s in ranked[: args.top]:
        print(f"  {s.total:.2f}  {c.id}  n={c.count:<5} {c.template[:80]}", file=sys.stderr)

    if args.no_llm:
        return EXIT_OK

    # Stage 4: the only paid, non-deterministic step
    try:
        provider = get_provider(args.provider)
        label = f"{provider.name} / {getattr(provider, 'model', '?')}"
        print(f"Asking {label} ...", file=sys.stderr)
        result = triage(ranked, provider, top_n=args.top)
    except ValueError as e:          # unknown provider name
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE
    except (LLMError, TriageError) as e:
        print(f"error: triage failed: {e}", file=sys.stderr)
        return EXIT_LLM

    # Stage 5: render and save
    md = render(result, ranked, source=str(args.logfile), provider=label, stats=stats)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{args.logfile.stem}-{datetime.now():%Y%m%d-%H%M%S}.md"
    path.write_text(md, encoding="utf-8")

    print(f"\nRoot cause ({result.model_confidence.value}): {result.probable_root_cause}")
    print(f"Report: {path}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())