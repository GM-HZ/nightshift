# Runtime State Migration Implementation Plan

## Scope

Implement Phase 3 of the `.nightshift` migration:

- add runtime storage resolution by repository layout
- refactor `StateStore` to use resolved runtime paths
- update the few direct runtime path call sites that bypass `StateStore`
- keep compatibility repositories unchanged

This slice does **not** migrate:

- user-space `~/.nightshift/`
- Work Order storage
- contract semantics
- delivery behavior

## Goal

NightShift should support two runtime storage modes:

- compatibility runtime storage
- layered runtime storage

Each repository must use exactly one authoritative runtime mode.

## Non-Goals

Do not implement in this slice:

- dual-write between `nightshift-data/` and `.nightshift/`
- report format redesign
- recovery behavior redesign
- config editing commands
- merge/deploy workflow changes

## Design Constraints

- compatibility repositories must continue using `nightshift-data/`
- layered runtime repositories must use `.nightshift/records/`, `.nightshift/runs/`, `.nightshift/artifacts/`, and `.nightshift/reports/`
- explicit report output config must still override the default report root
- existing callers should keep using `StateStore` APIs as much as possible

## Required Marker Semantics

Layered runtime storage is enabled only when the repository marker declares:

```yaml
layout_version: 1
project_config_source: layered
runtime_layout_source: layered
contract_storage_source: layered
```

Rules:

- if `runtime_layout_source` is absent or `compatibility`, runtime storage stays legacy
- `runtime_layout_source: layered` requires:
  - `project_config_source: layered`
- compatibility/project-config-only repositories must not accidentally switch runtime roots

## Task Breakdown

### Task 1: Runtime Storage Resolution Models

Extend config resolution to support runtime storage paths.

Suggested additions:

- extend `src/nightshift/config/models.py`
- extend `src/nightshift/config/loader.py`

Needed concepts:

- runtime storage mode enum
- resolved runtime storage roots

Suggested API:

- `resolve_runtime_storage(repo_root: Path) -> ResolvedRuntimeStorage`

The resolved object should include at least:

- records root
- active run path
- runs root
- alerts path
- artifacts root
- reports root

### Task 2: StateStore Refactor

Refactor `src/nightshift/store/state_store.py` so path construction goes through the runtime storage resolver instead of hardcoded `nightshift-data/` paths.

Expected behavior:

- current records
- active run pointer
- run states
- issue snapshots
- attempt records
- events
- alerts

all follow the active runtime storage mode.

### Task 3: Direct Artifact Path Call Sites

Update direct runtime-path users that bypass `StateStore`.

Known likely sites:

- `src/nightshift/orchestrator/run_orchestrator.py`
- `src/nightshift/orchestrator/recovery.py`

These should use the resolved artifact root instead of hardcoded `nightshift-data/runs/...`.

### Task 4: Reporting Integration

Ensure reporting still works in both modes:

- `StateStore`-backed report reads from the active runtime mode
- explicit configured report output path still wins
- default layered report root remains available through the resolver for future use

Likely file:

- `src/nightshift/reporting/minimal_report.py`

This may only need verification, not code changes, if `StateStore` absorbs the path migration fully.

### Task 5: Tests

Add or update tests for:

- compatibility runtime repositories behave unchanged
- layered runtime repositories write/read state from `.nightshift/`
- active run pointer moves to `.nightshift/records/active-run.json`
- alerts move to `.nightshift/records/alerts.ndjson`
- run history moves to `.nightshift/runs/`
- recovery/report paths still work in layered mode
- no dual-write occurs

Likely files:

- `tests/test_config_loader.py`
- `tests/test_state_store.py`
- `tests/test_minimal_report.py`
- `tests/test_recovery.py`
- `tests/test_run_orchestrator.py`

### Task 6: Docs

Update docs to explain:

- compatibility vs layered runtime storage
- runtime-only `.nightshift/` directories
- Phase 3 marker requirements
- report/artifact path implications

Likely files:

- `docs/architecture/product/runtime-state-migration.md`
- `docs/usage/configuration.md`
- `docs/usage/deployment.md`

## Verification

Required verification:

```bash
./.venv/bin/python -m pytest tests/test_config_loader.py tests/test_state_store.py tests/test_minimal_report.py tests/test_recovery.py tests/test_run_orchestrator.py -q
./.venv/bin/python -m pytest -q
```

If queue/delivery tests touch artifact paths indirectly, also run:

```bash
./.venv/bin/python -m pytest tests/test_queue_admission_service.py tests/test_queue_add_cli.py -q
```

## Suggested Implementation Order

1. add runtime storage resolution model and marker validation
2. refactor `StateStore` to use resolved paths
3. update direct artifact path call sites
4. add layered-mode runtime tests
5. sync docs
6. run targeted and full verification

## Success Criteria

This slice is complete when:

- compatibility repositories keep using `nightshift-data/` unchanged
- layered repositories store runtime state under `.nightshift/`
- `StateStore` is the central runtime path abstraction
- recovery, reporting, and orchestration still function in both modes
- docs describe Phase 3 without implying user-space migration is already done
