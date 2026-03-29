# Layered Project Config Implementation Plan

## Scope

Implement Phase 1 of the config and workspace migration plan:

- add layered project config support under `.nightshift/config/`
- add a repository migration marker under `.nightshift/config/migration.yaml`
- preserve full compatibility with root `nightshift.yaml`

This slice does **not** migrate runtime state, contracts, records, or reports.

## Goal

NightShift should be able to resolve project configuration in two modes:

- MVP compatibility mode:
  - authoritative config remains `nightshift.yaml`
- layered project config mode:
  - authoritative config lives under `.nightshift/config/`

The active mode must be determined explicitly, not guessed.

## Non-Goals

Do not implement in this slice:

- `~/.nightshift/` user-space config
- runtime path migration out of `nightshift-data/`
- contract storage migration into `.nightshift/contracts/`
- config editing commands
- full multi-file config decomposition if it complicates compatibility

## Design Constraints

- Existing operators and tests that use `nightshift.yaml` must continue to work unchanged.
- Layered mode must only activate when a repository migration marker is present.
- There must be only one authoritative project config source per repository mode.
- CLI precedence should remain:
  - CLI flags
  - project config
  - built-in defaults

User-level config remains out of scope for this slice.

## Target Behavior

### Compatibility Mode

If `.nightshift/config/migration.yaml` is absent:

- NightShift loads project config from root `nightshift.yaml`
- behavior remains unchanged from today

### Layered Mode

If `.nightshift/config/migration.yaml` is present and declares layered project config:

- NightShift loads project config from `.nightshift/config/`
- root `nightshift.yaml` is no longer authoritative
- if both exist, layered config wins

## Recommended First File Layout

To keep the first slice small, layered project config should begin with a single main file:

- `.nightshift/config/project.yaml`

Migration marker:

- `.nightshift/config/migration.yaml`

This keeps the path model layered without forcing immediate decomposition into many config files.

Later slices can split `project.yaml` if needed.

## Task Breakdown

### Task 1: Config Resolution Models

Add small config resolution models for:

- migration marker
- layout mode
- resolved config source metadata

Suggested additions:

- `src/nightshift/config/resolution.py`

Expected behavior:

- parse `.nightshift/config/migration.yaml`
- determine whether repository is in:
  - `compatibility`
  - `layered_project_config`

### Task 2: Loader Refactor

Refactor config loading so callers can resolve config by repository root, not only explicit file path.

Suggested changes:

- extend `src/nightshift/config/loader.py`

Add:

- `load_project_config(repo_root: Path) -> NightShiftConfig`
- `resolve_project_config_source(repo_root: Path) -> ResolvedConfigSource`

Keep:

- existing `load_config(path: Path)` for direct file loading and backward compatibility

### Task 3: Layered Config File Support

Teach the loader to read:

- `.nightshift/config/project.yaml`

when layered mode is enabled.

Behavior:

- layered mode + layered file present:
  - load layered file
- layered mode + layered file missing:
  - fail with a clear error
- compatibility mode:
  - ignore layered file unless explicitly requested in future work

### Task 4: CLI Integration

Update CLI bootstrap paths that currently assume explicit `nightshift.yaml` so they can also resolve config by repo root.

Important:

- existing `--config /path/to/nightshift.yaml` should continue to work
- repo-root-based flow should become compatible with future `.nightshift/config/project.yaml`

Prefer minimal integration in the CLI layer:

- if explicit `--config` is provided, keep existing behavior
- otherwise resolve by repo root and active layout mode

### Task 5: Tests

Add and update tests for:

- compatibility mode loads `nightshift.yaml`
- layered mode loads `.nightshift/config/project.yaml`
- layered mode fails cleanly without project config file
- migration marker absent means compatibility mode
- explicit direct `load_config(path)` remains unchanged

Likely files:

- `tests/test_config_loader.py`
- targeted CLI tests if any command path changes

### Task 6: Docs

Update user-facing docs to explain:

- current compatibility mode
- new Phase 1 layered project config option
- migration marker requirement

Likely files:

- `docs/usage/configuration.md`
- `docs/usage/install.md`
- possibly `README.md` if wording needs a short note

## Verification

Required verification for this slice:

```bash
./.venv/bin/python -m pytest tests/test_config_loader.py -q
./.venv/bin/python -m pytest -q
```

If CLI bootstrap code changes materially, also run targeted CLI tests that exercise config loading paths.

## Suggested Implementation Order

1. add resolution models and marker parsing
2. refactor loader with repo-root-aware config resolution
3. add layered config tests first
4. wire minimal CLI integration
5. update docs
6. run full verification

## Success Criteria

This slice is complete when:

- old repositories using `nightshift.yaml` work unchanged
- a repository with `.nightshift/config/migration.yaml` plus `.nightshift/config/project.yaml` can load config successfully
- the active config source is deterministic
- no runtime state migration is attempted
- docs describe both layouts clearly without implying full migration is already complete
