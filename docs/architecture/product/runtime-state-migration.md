# Runtime State Migration

## Status

Working product design aligned to `v4.2.1`.

This document defines Phase 3 of the `.nightshift` migration:

- mutable current records
- run history
- attempt artifacts
- reports

move from `nightshift-data/` into project-scoped runtime-only `.nightshift/` directories.

## Why This Exists

NightShift already has:

- layered project config
- layered contract storage
- project-scoped Work Orders

The remaining large legacy surface is runtime-only state under `nightshift-data/`.

That includes:

- current issue records
- active run pointer
- run state
- issue snapshots
- attempt records
- event log
- alerts
- report outputs

As long as those remain outside the `.nightshift/` model, the workspace architecture is still split across two different project layouts.

## Design Goal

NightShift should migrate runtime-only repository state into project `.nightshift/` directories while preserving:

- the current kernel APIs
- reporting
- recovery
- queue admission and execution behavior

This migration is about **runtime storage paths**, not a behavioral redesign.

## Non-Goals

This phase does not change:

- Work Order semantics
- IssueContract semantics
- delivery semantics
- user-space `~/.nightshift/`

It also does not require versioning runtime-only artifacts in git.

## Current Compatibility Runtime Layout

Today runtime state is primarily stored under:

- `nightshift-data/issue-records/`
- `nightshift-data/runs/`
- `nightshift-data/active-run.json`
- `nightshift-data/alerts.ndjson`
- `nightshift-data/reports/` in practice via config output paths

This is the authoritative runtime layout for compatibility repositories.

## Target Layered Runtime Layout

Layered runtime repositories should use:

- current records:
  - `.nightshift/records/current/`
- active run pointer:
  - `.nightshift/records/active-run.json`
- run history:
  - `.nightshift/runs/<run_id>/`
- attempt artifacts:
  - `.nightshift/artifacts/runs/<run_id>/attempts/<attempt_id>/`
- reports:
  - `.nightshift/reports/`
- alerts:
  - `.nightshift/records/alerts.ndjson`

## Why Split `records/`, `runs/`, `artifacts/`, And `reports/`

The split matches actual runtime responsibilities:

- `records/`
  - mutable current state
- `runs/`
  - authoritative run-scoped history
- `artifacts/`
  - heavy engine and validation byproducts
- `reports/`
  - operator-facing outputs

This is cleaner than letting everything continue to accumulate under one `nightshift-data/` root.

## Authority Rule

For any repository, runtime state must have exactly one authoritative mode.

### Compatibility Repositories

Authority remains:

- `nightshift-data/issue-records/`
- `nightshift-data/runs/`
- `nightshift-data/active-run.json`
- `nightshift-data/alerts.ndjson`

### Layered Runtime Repositories

Authority becomes:

- `.nightshift/records/current/`
- `.nightshift/runs/`
- `.nightshift/records/active-run.json`
- `.nightshift/records/alerts.ndjson`
- `.nightshift/artifacts/`
- `.nightshift/reports/`

No dual-write.

## Marker Extension

Phase 3 should continue the explicit migration pattern by using:

```yaml
layout_version: 1
project_config_source: layered
runtime_layout_source: layered
contract_storage_source: layered
```

This means:

- Phase 1 enables layered config
- Phase 2 enables layered contracts
- Phase 3 enables layered runtime state

## Why Runtime Migration Should Stay Explicit

Runtime migration touches:

- `StateStore`
- recovery
- reporting
- orchestration
- artifact lookup

It is the highest-risk path migration so far.

That is exactly why it should remain an explicit repository opt-in, not an implied side effect of layered config.

## Resolution Rules

NightShift should add a runtime storage resolver responsible for:

- current record root
- active run pointer path
- run history root
- alerts path
- artifact root
- default report root

All runtime storage APIs should go through this resolver.

Callers should not hardcode:

- `nightshift-data/issue-records/`
- `nightshift-data/runs/`
- `nightshift-data/active-run.json`
- `nightshift-data/alerts.ndjson`

## Preferred Refactor Boundary

The preferred integration point is:

- `StateStore`

`StateStore` already centralizes most runtime persistence.

So the migration should:

1. add a runtime storage resolver
2. refactor `StateStore` to use the resolved paths
3. keep callers unchanged as much as possible

This is much safer than pushing path selection into orchestrator, recovery, and reporting individually.

## Read Behavior During Migration

### Compatibility Runtime Mode

- read only legacy `nightshift-data/` locations

### Layered Runtime Mode

- read only layered `.nightshift/` runtime locations

If a repository declares layered runtime mode but the expected runtime paths are missing, NightShift should fail clearly rather than silently mixing old and new state.

## Write Behavior During Migration

### Compatibility Runtime Mode

- write only legacy runtime paths

### Layered Runtime Mode

- write only layered runtime paths

No dual-write.

## Report Output Rule

Reports need special handling because the current CLI also supports explicit configured output paths.

Recommended rule:

- runtime state resolver determines the default layered report root
- explicit report output configured in project config still wins

This preserves operator control while still giving the new layout a clean default location.

## Artifact Root Rule

Attempt artifact directories should also move under the runtime layout, but they should remain logically separate from run-state JSON:

- run-state JSON under `.nightshift/runs/`
- heavy attempt artifacts under `.nightshift/artifacts/`

This prevents run history directories from becoming overloaded with bulky engine output.

## Testing Strategy

Phase 3 tests should cover:

- compatibility runtime repositories behave unchanged
- layered runtime repositories write current records, runs, alerts, and active-run pointer under `.nightshift/`
- report generation reads the correct runtime roots
- recovery continues to find run history and attempt records in layered mode
- no mixed-mode dual-write occurs

## Documentation Impact

After Phase 3 implementation:

- usage docs should stop presenting `nightshift-data/` as the primary runtime layout for migrated repositories
- deployment docs should explain which `.nightshift/` directories are runtime-only
- architecture docs should show runtime state as fully inside project `.nightshift/`

## Recommendation

The next implementation slice should do only this:

- add runtime storage resolution based on repository layout mode
- refactor `StateStore` to use the resolver
- update the few direct runtime path call sites that bypass `StateStore`
- add compatibility and layered runtime tests

Do not combine runtime migration with user-space `~/.nightshift/` adoption in the same pass.
