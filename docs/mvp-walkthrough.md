# NightShift MVP Walkthrough

This walkthrough is for the current Python MVP that implements the `v4.2.1` kernel shape plus the first product workflow slices above it, including MVP PR delivery.

## Read This First

The active design source of truth is:

- `docs/superpowers/specs/README.md`
- `docs/superpowers/specs/2026-03-27-nightshift-v4.2.1-unified-spec.md`
- `docs/superpowers/specs/nightshift-v4.2.1/README.md`

The current implementation is intentionally narrower than the full architecture. It is a kernel MVP, not the full overnight product workflow.

For local multi-worktree development guidance, also read:

- `docs/local-development.md`

## What The MVP Can Do

- execute a single approved issue with `run-one`
- deliver an accepted issue into a GitHub pull request with `deliver`
- execute a single configured engine selection (`codex` or `claude`)
- create and reuse run-scoped persistence under `nightshift-data/`
- run validation gates and accept or reject attempts
- recover an interrupted run into a new controlling run
- generate a minimal historical report from persisted run history
- inspect and reprioritize the current queue state

## What The MVP Still Assumes

The repository no longer requires hand-authoring every execution artifact from scratch. The current workflow can now reach the kernel through:

- `split`
- `proposals update|approve|reject|publish`
- `issue ingest-github`
- `queue add`

Before running the kernel directly with `run-one`, the target repository must already contain:

- immutable issue contracts under `nightshift/issues/<issue_id>.yaml`
- current issue records under `nightshift-data/issue-records/<issue_id>.json`
- a valid `nightshift.yaml`

Reference shapes live in:

- `examples/nightshift.yaml`
- `examples/issues/NS-123.yaml`

Those example files are templates, not an automatically bootstrapped runnable repo state.

## Remaining Non-MVP Gaps

This branch intentionally stops short of the full `v4.2.1` product surface. The following items remain outside the current MVP:

- no multi-issue overnight scheduler, daemon runner, or stop control loop
- no merge automation or review-sync workflow after PR creation
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

`engine_preferences.fallback` and `runner.fallback_engine` are currently reserved fields.
The MVP harness does not auto-switch engines after a failure. If the selected engine fails, the run fails and the operator should inspect the persisted attempt record and artifacts directly.

## Install And Verify

```bash
python -m pip install -e .
python -m pytest -v
```

If multiple worktrees or editable installs exist on the same machine, prefer the explicit import-path pattern documented in `docs/local-development.md`.

## CLI Surface

```bash
python -m nightshift.cli.main --help
python -m nightshift.cli.main queue --help
```

Current commands:

- `split`
- `proposals show`
- `proposals update`
- `proposals approve`
- `proposals reject`
- `proposals publish`
- `issue ingest-github`
- `queue add`
- `run-one`
- `run`
- `deliver`
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

### 2. Ingest And Admit A Reviewed GitHub Issue

```bash
python -m nightshift.cli.main issue ingest-github \
  --repo-full-name GM-HZ/nightshift \
  --issue 7 \
  --materialize-only \
  --config /path/to/repo/nightshift.yaml

python -m nightshift.cli.main queue add GH-7 \
  --config /path/to/repo/nightshift.yaml
```

### 3. Run One Approved Issue

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

### 4. Deliver An Accepted Issue

```bash
python -m nightshift.cli.main deliver \
  --issues GH-7 \
  --config /path/to/repo/nightshift.yaml
```

Or as a convenience wrapper:

```bash
python -m nightshift.cli.main run \
  --issues GH-7 \
  --config /path/to/repo/nightshift.yaml \
  --deliver
```

Delivery prerequisites:

- the issue must already be `done + accepted`
- `product.delivery.repo_full_name` must be configured
- `GITHUB_TOKEN` or `NIGHTSHIFT_GITHUB_TOKEN` must be available
- the accepted issue worktree must still exist
- the local repository must have a writable `origin` remote

### 5. Recover An Interrupted Run

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

### 6. Generate A Minimal Historical Report

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
