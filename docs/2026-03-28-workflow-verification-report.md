# NightShift Workflow Verification Report

Date: 2026-03-28

This report captures a real operator-style rehearsal against fresh temporary repositories after the `v4.2.1` MVP implementation landed on `master`.

## Scope

The rehearsal covered two layers:

- Layer 1: kernel smoke run using `queue`, `run-one`, and `report`
- Layer 2: failure and recovery drill using `recover --run` against hand-seeded persisted source runs

The goal was not to prove every branch of unit-tested behavior again. The goal was to verify that the documented operator flow works end to end against a real repository and to surface gaps that only appear outside test doubles.

## Environment Notes

The first smoke run accidentally used a Python environment whose editable install still pointed at an older worktree. That caused the CLI to execute stale code and produced a misleading engine selection result.

For the authoritative rehearsal, commands were run with:

```bash
PYTHONPATH=/Users/gongmeng/dev/code/nightshift/src \
PATH="/Users/gongmeng/dev/code/nightshift/.worktrees/nightshift-v4.2.1-mvp/.venv/bin:$PATH" \
python -m nightshift.cli.main ...
```

This is important: in the current multi-worktree setup, it is possible to run the right dependency environment against the wrong source tree if the editable install target is stale.

## Rehearsal Repositories

- First-pass exploratory repo: `/private/tmp/nightshift-workflow-rehearsal`
- Authoritative repo for current `master`: `/tmp/nightshift-workflow-rehearsal-master`

The authoritative repo was seeded with:

- `nightshift.yaml`
- `nightshift/issues/NS-SMOKE-1.yaml`
- `nightshift-data/issue-records/NS-SMOKE-1.json`
- a minimal git repository with one initial commit on `main`

## Layer 1 Results

### Queue inspection

These commands worked as expected:

```bash
python -m nightshift.cli.main queue status --repo /tmp/nightshift-workflow-rehearsal-master
python -m nightshift.cli.main queue show NS-SMOKE-1 --repo /tmp/nightshift-workflow-rehearsal-master
```

Observed result:

- the hand-seeded issue was listed as schedulable
- queue output matched the persisted issue record

### Single-issue execution

Command:

```bash
python -m nightshift.cli.main run-one NS-SMOKE-1 \
  --config /tmp/nightshift-workflow-rehearsal-master/nightshift.yaml
```

Observed result:

- the orchestrator selected `codex`
- the real engine invocation exited with code `1`
- the run closed as `aborted`
- the current issue record returned to `ready + aborted`
- run-scoped state, attempt record, issue snapshot, and events were persisted

The persisted attempt record showed the expected selected engine:

- `engine_name=codex`
- `attempt_state=aborted`
- `engine_outcome="command exited with code 1"`

### Historical report

Command:

```bash
python -m nightshift.cli.main report \
  --config /tmp/nightshift-workflow-rehearsal-master/nightshift.yaml
```

Observed result:

- the report was generated successfully from run-scoped persisted history
- the report summarized the aborted run correctly
- the configured report output file was also written under `.reports/`

### Layer 1 conclusion

The kernel flow is operational:

- queue inspection works
- single-issue execution persists the right structures
- engine failure closes the run safely
- historical reporting works off persisted run history

The main user-facing weakness in this layer is CLI failure presentation, not state integrity.

## Layer 2 Results

Two recovery scenarios were rehearsed against hand-seeded source runs.

### Scenario A: executing attempt with no durable engine outcome

Source state:

- source run: `RUN-RECOVER-EXEC-SOURCE`
- source attempt: `ATTEMPT-RECOVER-EXEC-SOURCE`
- attempt state: `executing`
- `engine_outcome=null`

Command:

```bash
python -m nightshift.cli.main recover \
  --run RUN-RECOVER-EXEC-SOURCE \
  --repo /tmp/nightshift-workflow-rehearsal-master
```

Observed result:

- source run was marked `aborted`
- a new recovery run was created
- a new recovery attempt was created
- the recovery attempt was normalized to `aborted`
- the issue record moved to `ready + aborted`
- `report --run <recovery_run_id>` succeeded

This validated the intended “fail closed” recovery path for interrupted execution without a durable engine outcome.

### Scenario B: validating attempt with durable engine outcome

Source state:

- source run: `RUN-RECOVER-VALIDATE-SOURCE`
- source attempt: `ATTEMPT-RECOVER-VALIDATE-SOURCE`
- attempt state: `validating`
- `engine_outcome="command completed successfully"`
- workspace path set to the repository root so validation commands could rerun

Command:

```bash
python -m nightshift.cli.main recover \
  --run RUN-RECOVER-VALIDATE-SOURCE \
  --repo /tmp/nightshift-workflow-rehearsal-master
```

Observed result:

- source run was marked `aborted`
- a new recovery run was created
- validation reran successfully
- the recovery attempt was marked `accepted`
- the issue record moved to `done + accepted`
- `report --run <recovery_run_id>` succeeded

This validated the intended “resume at validation boundary” recovery path.

## Confirmed Strengths

- Real repos can be hand-seeded and driven through the current MVP commands.
- `run-one` closes engine failure safely instead of silently accepting partial work.
- Historical reporting is built from run-scoped persisted state and works in practice.
- Recovery semantics are real, not just test doubles:
  executing-without-outcome becomes a new aborted recovery run.
  validating-with-durable-state reruns validation and can complete successfully.

## Confirmed Gaps

### 1. Resolved after rehearsal: `run-one` surfaced engine failures as a Python traceback

In the smoke run, engine failure returned a full traceback ending in:

```text
RuntimeError: engine outcome engine_crash cannot be accepted
```

This was technically correct but operator-hostile at rehearsal time. It has since been fixed in the follow-up CLI patch so `run-one` returns a short failure summary instead of a raw traceback.

### 2. Resolved after rehearsal: recovery terminal run states were not clearing active fields

Both of these persisted run states retained active pointers even after terminal completion:

- aborted recovery run: `/tmp/nightshift-workflow-rehearsal-master/nightshift-data/runs/RUN-ff74a4fc/run-state.json`
- completed recovery run: `/tmp/nightshift-workflow-rehearsal-master/nightshift-data/runs/RUN-3a6fa49f/run-state.json`

Observed behavior:

- `run_state=aborted|completed`
- `active_issue_id` still set
- `active_attempt_id` still set

This was a real normalization bug at rehearsal time. It has since been fixed in the follow-up recovery patch so terminal recovery runs now clear active fields.

### 3. Resolved after rehearsal: recovery attempt metadata was only partially re-authored

In the accepted recovery attempt:

- file: `/tmp/nightshift-workflow-rehearsal-master/nightshift-data/runs/RUN-3a6fa49f/attempts/ATTEMPT-4bdfb10d.json`

Observed behavior:

- `artifact_dir` still points at the source run artifact path
- `ended_at` is still `null`
- `duration_ms` is still `null`

This was a real normalization bug at rehearsal time. It has since been fixed in the follow-up recovery patch so the recovery attempt owns its recovery-run artifact path and terminal metadata.

### 4. Multi-worktree local execution is easy to mis-run

The first rehearsal accidentally executed stale code because the virtual environment still pointed at an older editable install. That is not a product bug, but it is a real development workflow hazard for this repository.

The current team workflow should assume that:

- worktree-bound editable installs can drift
- local rehearsal commands should either use a repo-local venv for the active checkout or set `PYTHONPATH` explicitly

## Assessment

The important news is positive: the current `v4.2.1` MVP is operational as a real kernel. The core execution, persistence, reporting, and recovery model all survived a real operator-style rehearsal.

The remaining issues are now concentrated in development workflow hardening, not in the main architecture:

- make local execution guidance safer in multi-worktree development

## Recommended Next Fix Order

1. Add a short local development note documenting safe command invocation when multiple editable installs or worktrees exist.
