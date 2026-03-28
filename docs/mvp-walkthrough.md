# NightShift MVP Walkthrough

This walkthrough is for the current Python MVP that implements the `v4.2.1` kernel shape.

## Read This First

The active design source of truth is:

- `docs/superpowers/specs/README.md`
- `docs/superpowers/specs/2026-03-27-nightshift-v4.2.1-unified-spec.md`
- `docs/superpowers/specs/nightshift-v4.2.1/README.md`

The current implementation is intentionally narrower than the full architecture. It is a kernel MVP, not the full overnight product workflow.

## What The MVP Can Do

- execute a single approved issue with `run-one`
- select `codex` or `claude`, including configured fallback behavior
- create and reuse run-scoped persistence under `nightshift-data/`
- run validation gates and accept or reject attempts
- recover an interrupted run into a new controlling run
- generate a minimal historical report from persisted run history
- inspect and reprioritize the current queue state

## What The MVP Still Assumes

The MVP does not yet include an issue ingestion or approval CLI. Before running the kernel, the target repository must already contain:

- immutable issue contracts under `nightshift/issues/<issue_id>.yaml`
- current issue records under `nightshift-data/issue-records/<issue_id>.json`
- a valid `nightshift.yaml`

Reference shapes live in:

- `examples/nightshift.yaml`
- `examples/issues/NS-123.yaml`

Those example files are templates, not an automatically bootstrapped runnable repo state.

## Remaining Non-MVP Gaps

This branch intentionally stops short of the full `v4.2.1` product surface. The following items remain outside the current MVP:

- no requirement splitter or approval ingestion flow
- no `queue add` command
- no multi-issue overnight scheduler, daemon runner, or stop control loop
- no delivery automation for branch-ready, PR-opened, reviewed, merged, or closed states
- no operator log browsing command such as `logs --issue`
- no rich report generator beyond the current minimal JSON historical report
- retry budgets, circuit breaker behavior, alert delivery channels, and top-level validation command groups are not yet fully wired into orchestration policy

Treat these as the explicit next layer above the current kernel MVP, not as hidden unfinished work inside the implemented slice set.

## Expected Repository Layout

```text
<target-repo>/
  nightshift/
    issues/
      NS-123.yaml
  nightshift-data/
    issue-records/
      NS-123.json
    runs/
      <run_id>/
        run-state.json
        issues/
        attempts/
        artifacts/
          attempts/
        events.ndjson
  nightshift.yaml
```

## Engine Names

Use NightShift adapter names in config and issue preferences:

- `codex`
- `claude`

Do not put raw model names like `gpt-5` into `runner.default_engine` or `engine_preferences.primary`; the current registry resolves adapter names, not model identifiers.

## Install And Verify

```bash
python -m pip install -e .
python -m pytest -v
```

## CLI Surface

```bash
python -m nightshift.cli.main --help
python -m nightshift.cli.main queue --help
```

Current commands:

- `run-one`
- `recover`
- `report`
- `queue status`
- `queue show`
- `queue reprioritize`

## Typical Operator Flow

### 1. Inspect The Queue

```bash
python -m nightshift.cli.main queue status --repo /path/to/repo
python -m nightshift.cli.main queue show NS-123 --repo /path/to/repo
python -m nightshift.cli.main queue reprioritize NS-123 high --repo /path/to/repo
```

### 2. Run One Approved Issue

```bash
python -m nightshift.cli.main run-one NS-123 \
  --config /path/to/repo/nightshift.yaml
```

If `project.repo_path` is set in `nightshift.yaml`, `--repo` may be omitted. If both are provided, `--repo` wins.

Success or rejection is printed on stdout. Durable state is written under `nightshift-data/`.

Prerequisites:

- the target repo must be a git repository
- the configured engine binary must be installed and available on `PATH`
- the issue contract and issue record must already exist

### 3. Recover An Interrupted Run

```bash
python -m nightshift.cli.main recover \
  --run RUN-20260328-001 \
  --repo /path/to/repo
```

Recovery semantics in the current MVP:

- the source run is marked `aborted`
- a new controlling run is created
- interrupted attempts without durable engine outcome are normalized to `aborted`
- attempts already in `validating` are revalidated from persisted state

The command emits JSON including both `source_run_id` and `recovery_run_id`.

### 4. Generate A Minimal Historical Report

```bash
python -m nightshift.cli.main report --repo /path/to/repo
python -m nightshift.cli.main report --config /path/to/repo/nightshift.yaml
python -m nightshift.cli.main report --config /path/to/repo/nightshift.yaml --run RUN-20260328-001
```

Report semantics in the current MVP:

- reads only persisted run-scoped history from `nightshift-data/runs/<run_id>/`
- prefers the active run when `--run` is omitted
- otherwise falls back to the latest persisted run
- writes `<run_id>.json` under `report.output_directory` when `--config` is provided

## Where To Look In Code

- CLI wiring: `src/nightshift/cli/app.py`
- run orchestration: `src/nightshift/orchestrator/run_orchestrator.py`
- recovery flow: `src/nightshift/orchestrator/recovery.py`
- reporting: `src/nightshift/reporting/minimal_report.py`
- issue registry: `src/nightshift/registry/issue_registry.py`
- state store: `src/nightshift/store/state_store.py`

## Verification Baseline

At the end of the current MVP slice set, the expected local verification command is:

```bash
python -m pytest -v
```
