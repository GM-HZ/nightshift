# NightShift

NightShift is an overnight AI coding harness. This repository now contains both the `v4.2.1` architecture spec set and a Python MVP kernel that can execute a single issue, validate it, recover interrupted runs, and emit a minimal historical report.

## Current Status

- Current implementation target: `v4.2.1`
- Current CLI surface: `run-one`, `run`, `recover`, `report`, `queue status`, `queue show`, `queue add`, `queue reprioritize`, `issue ingest-github`
- Current engine adapters: `codex`, `claude`
- Current scope: single-issue execution flow plus persistence, validation, recovery, and run-scoped reporting

## Repository Map

- `src/nightshift/`: Python MVP kernel implementation
- `tests/`: executable behavior and regression coverage
- `examples/`: reference config and issue contract shapes
- `docs/superpowers/specs/`: architecture history and current spec set
- `docs/mvp-walkthrough.md`: implementation-facing usage notes for the current MVP
- `docs/2026-03-28-workflow-verification-report.md`: real operator rehearsal results and confirmed workflow gaps
- `docs/local-development.md`: safe local execution guidance for multi-worktree development
- `docs/architecture/README.md`: current architecture entry point, split into kernel and product workflow views

## Current Recommended Entry Points

- Specs index: `docs/superpowers/specs/README.md`
- Current architecture: `docs/superpowers/specs/2026-03-27-nightshift-v4.2.1-unified-spec.md`
- Current detailed design pack: `docs/superpowers/specs/nightshift-v4.2.1/README.md`
- MVP walkthrough: `docs/mvp-walkthrough.md`
- Latest workflow verification: `docs/2026-03-28-workflow-verification-report.md`
- Local development note: `docs/local-development.md`
- Architecture entry point: `docs/architecture/README.md`

## Current MVP Boundaries

What works now:

- load `nightshift.yaml`
- read immutable issue contracts and current issue records
- create issue worktrees and snapshots
- execute via one selected engine adapter: `codex` or `claude`
- run validation gates
- persist run state, issue snapshots, attempt records, events, and alerts
- recover interrupted runs into a new controlling run
- generate a minimal report from run-scoped persisted history

Current engine selection semantics:

- `run-one` selects exactly one engine per attempt
- selection order is `IssueContract.engine_preferences.primary`, then `runner.default_engine`
- `engine_preferences.fallback` and `runner.fallback_engine` are currently reserved schema fields
- the MVP harness does not auto-switch engines after a failure; operators should inspect persisted attempt records and artifacts directly

What is intentionally not in the MVP yet:

- requirement splitter
- PR dispatcher / merge automation
- notifications and dashboards
- unattended multi-issue overnight scheduling policy beyond the current sequential `run --issues` / `run --all` primitives

## Remaining Non-MVP Gaps

The current branch is intentionally not a full `v4.2.1` product-complete implementation. These gaps are known and not bugs in the current MVP scope:

- no end-to-end intake workflow yet: `issue ingest-github`, `queue add`, `run --issues`, and `run --all` now exist, but splitter-driven issue creation and proposal review UI are still absent
- no daemonized multi-issue overnight control loop yet: `run --issues` and `run --all` now exist, but `run --daemon` and `stop` are not implemented
- no richer queue approval workflow yet beyond `queue add` and current reprioritization
- no delivery automation yet: branch handoff, PR opening, review sync, and merge workflows are not wired
- no operator log views yet: `logs --issue` is not implemented
- config sections such as `retry`, `alerts`, and top-level validation command groups are modeled, but only minimally wired in the MVP
- no rich morning report generator yet beyond the current minimal JSON historical report

## Local Verification

```bash
python -m pytest -v
```

If you are working across multiple worktrees or editable installs, read `docs/local-development.md` first and prefer an explicit `PYTHONPATH` plus known interpreter path.
