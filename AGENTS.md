# AGENTS.md

## Current handoff

Before changing code, read `docs/superpowers/SESSION-STATE.md` and the active plan named there. As of the latest sync, P0 through P3 (scaffold, MVP download/convert, library persistence, local Web UI) are implemented; the next planned work is P4 update scheduling.

## Agent skills

### Issue tracker

Issues and PRDs live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, default vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
