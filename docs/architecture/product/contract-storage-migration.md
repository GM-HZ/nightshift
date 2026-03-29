# Contract Storage Migration

## Status

Working product design aligned to `v4.2.1`.

This document defines Phase 2 of the `.nightshift` migration:

- contract storage moves toward `.nightshift/contracts/`
- current compatibility repositories keep using:
  - `nightshift/issues/`
  - `nightshift/contracts/`

The design assumes Phase 1 layered project config already exists.

## Why This Exists

NightShift now materializes `Execution Work Orders` into immutable `IssueContract` artifacts.

The current on-disk contract model is split across two legacy paths:

- current contract:
  - `nightshift/issues/<issue_id>.yaml`
- revision history:
  - `nightshift/contracts/<issue_id>/...`

That shape works, but it does not match the emerging `.nightshift` project workspace model.

We need to migrate contracts into the new project space without breaking:

- the already working queue freeze flow
- record lookups
- run orchestration
- delivery and reporting

## Design Goal

NightShift should support two contract storage modes:

- compatibility contract storage
- layered contract storage

Only one mode should be authoritative for a given repository.

## Non-Goals

This migration does not yet move:

- mutable issue records
- run history
- attempt artifacts
- reports

It also does not change contract semantics.

This is a storage migration, not a contract model redesign.

## Current Compatibility Contract Layout

Compatibility repositories keep using:

- `nightshift/issues/<issue_id>.yaml`
- `nightshift/contracts/<issue_id>/<sequence>-<revision>.yaml`

Authority remains in those paths until the repository enters layered contract storage mode.

## Target Layered Contract Layout

Layered repositories should use:

- current frozen contract:
  - `.nightshift/contracts/current/<issue_id>.yaml`
- revision history:
  - `.nightshift/contracts/history/<issue_id>/<sequence>-<revision>.yaml`

This keeps the same logical split:

- current frozen contract
- revision history

but moves both under one project-scoped layered root.

## Why Use `current/` And `history/`

This avoids two common problems:

1. mixing “the active contract” with archival history in one directory
2. forcing every caller to know whether it wants the latest or historical view

The first-pass API can stay simple:

- `get_contract(issue_id)` reads `current/`
- `list_contract_revisions(issue_id)` reads `history/`

## Authority Rule

For any repository, contract storage must have exactly one authoritative mode.

### Compatibility Repositories

Authority is:

- `nightshift/issues/`
- `nightshift/contracts/`

### Layered Repositories

Authority is:

- `.nightshift/contracts/current/`
- `.nightshift/contracts/history/`

NightShift must not dual-write both storage modes as long-term authorities.

## Layout Selection Rule

Contract storage mode should be selected from the Phase 1 migration marker.

### Compatibility Mode

If:

- `.nightshift/config/migration.yaml` is absent

or

- `project_config_source: compatibility`

then contract storage remains compatibility mode.

### Layered Contract Mode

If the repository later declares contract storage migration explicitly, layered contract paths become authoritative.

Recommended next marker extension:

```yaml
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
contract_storage_source: layered
```

This keeps contract storage migration independent from record/run runtime migration.

## Why Add A Separate Contract Storage Marker

Phase 1 already separated project config migration from runtime migration.

Contract storage deserves the same treatment.

If contract migration were implied automatically by `project_config_source: layered`, we would lose the ability to:

- migrate config first
- migrate contracts second
- keep runtime state legacy longer

Separate migration switches are worth the extra explicitness.

During this phase, the marker combination below is invalid and should fail clearly:

```yaml
layout_version: 1
project_config_source: compatibility
runtime_layout_source: compatibility
contract_storage_source: layered
```

Layered contract storage requires layered project config first.

## Resolution Rules

NightShift should introduce a contract path resolver with these responsibilities:

- determine authoritative contract mode for the repository
- return the active current-contract directory
- return the active revision-history directory

All contract reads and writes should go through this resolver.

Callers should not hardcode:

- `nightshift/issues/`
- `nightshift/contracts/`
- `.nightshift/contracts/...`

## Read Behavior During Migration

### Repository In Compatibility Mode

- reads only legacy contract locations

### Repository In Layered Contract Mode

- reads only layered contract locations

This is intentional.

The migration plan should not normalize dual reads forever.

If a repository is marked as layered contract storage but the layered current contract is missing, NightShift should fail clearly.

## Write Behavior During Migration

### Compatibility Mode

- writes current contract to `nightshift/issues/`
- writes history to `nightshift/contracts/`

### Layered Contract Mode

- writes current contract to `.nightshift/contracts/current/`
- writes history to `.nightshift/contracts/history/`

No dual-write.

## Compatibility Strategy

The migration should still be additive in rollout order:

1. introduce resolver and marker extension
2. keep compatibility repositories unchanged
3. allow layered repositories to opt into layered contract storage
4. update docs and examples
5. only later consider de-emphasizing legacy contract paths

## API Impact

The main impacted component is:

- `IssueRegistry`

It should stop hardcoding contract paths directly and instead ask a resolver for:

- current contract path for `issue_id`
- revision history directory for `issue_id`

Issue record storage remains unchanged in this phase.

## Testing Strategy

Phase 2 tests should cover:

- compatibility repository writes current and revision contracts to legacy paths
- layered contract repository writes current and revision contracts to layered paths
- `get_contract()` resolves the correct authoritative location
- `list_contract_revisions()` resolves the correct authoritative history location
- no mixed-mode dual-write occurs

## Documentation Impact

After Phase 2 implementation:

- usage docs should describe legacy vs layered contract locations
- architecture docs should point to `.nightshift/contracts/` as the new target for migrated repositories
- current compatibility docs must remain explicit for old repositories

## Recommendation

The next implementation slice should do only this:

- add contract storage resolution based on repository layout marker
- refactor `IssueRegistry` to use the resolver
- add compatibility and layered-mode tests

Do not combine contract migration with record/run migration in the same implementation pass.
