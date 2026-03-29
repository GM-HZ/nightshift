# Config And Workspace Migration Plan

## Status

Working product design aligned to `v4.2.1`.

This document defines how NightShift should migrate from the current MVP compatibility layout to the layered `.nightshift` model without breaking the already working kernel and product workflow.

## Why This Exists

NightShift currently has three overlapping storage/config surfaces:

- root `nightshift.yaml`
- repo-local `nightshift-data/`
- emerging repo-local `.nightshift/` assets such as Work Orders

That overlap was acceptable while proving the kernel and first product chain.

It is not the right long-term operating shape.

We need a migration path that:

- preserves the current working CLI and tests
- avoids a flag day rewrite
- keeps operator expectations stable
- gradually moves shared project state into `.nightshift/`
- keeps secrets and machine-local state out of the repository

## Migration Goals

The migration should result in:

- user-level state under `~/.nightshift/`
- project-level state under `<repo>/.nightshift/`
- a clean split between versioned and runtime-only project data
- compatibility shims for the current MVP layout until migration is complete

## Non-Goals

This migration plan does not require:

- immediate removal of `nightshift.yaml`
- immediate relocation of every runtime file
- a one-shot rewrite of all storage paths
- breaking backward compatibility for existing operators

## Current Compatibility Layout

Today NightShift expects or emits:

- `nightshift.yaml`
- `nightshift/issues/`
- `nightshift/contracts/`
- `nightshift-data/issue-records/`
- `nightshift-data/runs/`
- `nightshift-data/active-run.json`
- `nightshift-data/alerts.ndjson`

Work Orders are already moving toward:

- `.nightshift/work-orders/WO-<id>.md`

That means the project is already in a partial transition state.

## Target Layout

### User Space

```text
~/.nightshift/
  config/
  auth/
  engines/
  skills/
  plugins/
  cache/
  logs/
  state/
```

### Project Space

```text
.nightshift/
  config/
  work-orders/
  contracts/
  records/
  archive/
  runs/
  artifacts/
  reports/
```

## Versioned vs Runtime-Only

### Versioned Project Directories

- `.nightshift/config/`
- `.nightshift/work-orders/`
- `.nightshift/contracts/`
- `.nightshift/archive/`

### Runtime-Only Project Directories

- `.nightshift/records/`
- `.nightshift/runs/`
- `.nightshift/artifacts/`
- `.nightshift/reports/`

The exact git policy for individual files inside `records/` may still evolve, but the default assumption for the first migration phase should be runtime-only.

## Compatibility Principle

Migration should be additive before it becomes subtractive.

NightShift should first learn to:

1. read both old and new locations
2. prefer the new location when both exist
3. write to the new location once a repository is migrated
4. keep compatibility reads for at least one additional phase

This avoids a brittle flag day and supports mixed repositories during the transition.

## Source-Of-Truth Rule During Migration

During migration, there must still be only one authoritative source for each artifact class.

Recommended temporary authority rules:

- project config:
  - authority remains `nightshift.yaml` until the repository explicitly migrates
- work orders:
  - authority is `.nightshift/work-orders/`
- contracts:
  - authority remains `nightshift/issues/` and `nightshift/contracts/` until contract storage migrates
- issue records:
  - authority remains `nightshift-data/issue-records/` until records migration
- run history and artifacts:
  - authority remains `nightshift-data/runs/` until runtime migration

This plan intentionally avoids dual-write authority.

## Repository Migration Marker

The project needs a simple explicit marker so NightShift can know when to prefer the layered layout.

Recommended first marker:

- `.nightshift/config/migration.yaml`

Suggested contents:

```yaml
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
```

If this marker is absent, NightShift should assume MVP compatibility mode.

## Migration Phases

### Phase 0: Compatibility Baseline

Purpose:

- keep current working repositories stable
- document the target model
- avoid immediate path churn

Expected state:

- `nightshift.yaml` remains primary config
- `nightshift-data/` remains primary runtime store
- `.nightshift/work-orders/` is already valid and active

### Phase 1: Layered Project Config

Introduce:

- `.nightshift/config/`

Goal:

- move project defaults from root `nightshift.yaml` into layered project config files

Compatibility behavior:

- load layered config if migration marker says layered
- otherwise load `nightshift.yaml`
- if both exist in layered mode, layered config wins

Do not migrate runtime state yet.

### Phase 2: Contract Storage Migration

Introduce:

- `.nightshift/contracts/`

Goal:

- move frozen contract storage from:
  - `nightshift/issues/`
  - `nightshift/contracts/`
  into one project-scoped layered contract surface

Compatibility behavior:

- read new contracts first when repository is in layered mode
- fallback to legacy locations while compatibility remains enabled

### Phase 3: Record And Run Runtime Migration

Introduce:

- `.nightshift/records/`
- `.nightshift/runs/`
- `.nightshift/artifacts/`
- `.nightshift/reports/`

Goal:

- move mutable current records and run-scoped runtime data out of `nightshift-data/`

Compatibility behavior:

- runtime path resolver prefers layered mode when enabled
- legacy reads remain available for old repositories

### Phase 4: User Space Adoption

Introduce:

- `~/.nightshift/config/`
- `~/.nightshift/auth/`
- related user directories

Goal:

- separate secrets and user defaults from repo config

Compatibility behavior:

- CLI flags still win
- project config overrides user defaults
- environment variables continue to work for sensitive runtime integration

### Phase 5: Legacy Path De-Emphasis

At this point:

- docs stop presenting `nightshift.yaml` and `nightshift-data/` as primary paths
- compatibility support remains, but is explicitly legacy

Only after that should we consider legacy removal.

## Suggested Resolution Order

The migration should proceed in this order:

1. project config loader
2. contract storage
3. runtime state directories
4. user-space config and auth
5. docs and examples cutover

This order keeps runtime breakage risk low and preserves the already validated kernel flow.

## Required Compatibility Behaviors

During migration, NightShift should support:

- path resolution by layout mode
- explicit operator messaging about which layout is active
- migration-safe defaults
- repository-local migration markers
- deterministic precedence between CLI, project config, user config, and defaults

## CLI And UX Requirements

Migration should not force operators to memorize hidden path rules.

The CLI should eventually expose:

- current active layout mode
- config source path
- runtime storage root
- whether a repository is still in MVP compatibility mode

That does not need to be implemented in the first migration slice, but it should be a stated requirement.

## Testing Strategy

Each migration slice should verify:

- old-layout repository still works unchanged
- new-layout repository works when migration marker is enabled
- mixed read compatibility behaves predictably
- no artifact class has two writable authoritative locations at the same time

## Open Design Questions

- Whether some `records/` files should later become versioned summaries rather than runtime-only state
- Whether global auth should ultimately remain file-based or move behind keychain references
- Whether contract archive material should live entirely under `.nightshift/archive/` or remain split by artifact class

## Recommendation

Do not attempt a full migration in one implementation pass.

The next implementation slice should focus only on:

- adding layered project config support under `.nightshift/config/`
- defining repository migration markers
- keeping `nightshift.yaml` compatibility intact

That is the smallest step that moves NightShift toward the new model without destabilizing the current working product chain.
