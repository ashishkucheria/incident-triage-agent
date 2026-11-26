# Incident Triage Agent

Reads application logs, groups related errors, and uses an LLM to draft a
root-cause summary and postmortem.

> Status: in progress (built step by step as a learning project).

## Pipeline (planned)
1. **Ingest**: parse raw log lines into structured events
2. **Template**: mask variable parts (IDs, IPs, numbers) so similar lines group
3. **Cluster**: group events by template and time window; rank by burst/severity
4. **Triage**: send top clusters to an LLM (pluggable provider); validate its output
5. **Report**: render an incident summary and postmortem draft (Markdown)
6. **Evaluate**: measure accuracy on labelled public data (Loghub)

## Data
Public datasets only (Loghub: https://github.com/logpai/loghub). No employer data.
