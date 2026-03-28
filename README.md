# NightShift

NightShift is an overnight AI coding harness. This repository now contains both the `v4.2.1` architecture spec set and a Python MVP kernel that can execute a single issue, validate it, recover interrupted runs, and emit a minimal historical report.

## Current Status

- Current implementation target: `v4.2.1`
- Current CLI surface: `run-one`, `recover`, `report`, `queue status`, `queue show`, `queue reprioritize`
- Current engine adapters: `codex`, `claude`
- Current scope: single-issue execution flow plus persistence, validation, recovery, and run-scoped reporting

## Repository Map

- `src/nightshift/`: Python MVP kernel implementation
- `tests/`: executable behavior and regression coverage
- `examples/`: reference config and issue contract shapes
- `docs/superpowers/specs/`: architecture history and current spec set
- `docs/mvp-walkthrough.md`: implementation-facing usage notes for the current MVP

## Current Recommended Entry Points

- Specs index: `docs/superpowers/specs/README.md`
- Current architecture: `docs/superpowers/specs/2026-03-27-nightshift-v4.2.1-unified-spec.md`
- Current detailed design pack: `docs/superpowers/specs/nightshift-v4.2.1/README.md`
- MVP walkthrough: `docs/mvp-walkthrough.md`

## Current MVP Boundaries

What works now:

- load `nightshift.yaml`
- read immutable issue contracts and current issue records
- create issue worktrees and snapshots
- execute via `codex` or `claude`
- run validation gates
- persist run state, issue snapshots, attempt records, events, and alerts
- recover interrupted runs into a new controlling run
- generate a minimal report from run-scoped persisted history

What is intentionally not in the MVP yet:

- requirement splitter
- PR dispatcher / merge automation
- notifications and dashboards
- unattended multi-issue overnight scheduling policy beyond the current queue primitives

## Local Verification

```bash
python -m pytest -v
```
