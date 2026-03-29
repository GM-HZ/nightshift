# Contract Storage Migration Implementation Plan

## Scope

Implement Phase 2 of the `.nightshift` migration:

- add contract storage resolution by repository layout
- refactor `IssueRegistry` to use resolved contract paths
- keep compatibility repositories unchanged
- allow explicitly layered repositories to use `.nightshift/contracts/`

This slice does **not** migrate:

- mutable issue records
- run history
- attempt artifacts
- reports

## Goal

NightShift should support two contract storage modes:

- compatibility contract storage
- layered contract storage

Each repository must use exactly one authoritative contract mode.

## Non-Goals

Do not implement in this slice:

- record storage migration
- run/artifact migration
- user-space config/auth
- contract semantics changes
- queue/runtime behavior changes unrelated to contract paths

## Design Constraints

- Compatibility repositories must continue using:
  - `nightshift/issues/`
  - `nightshift/contracts/`
- Layered contract repositories must use:
  - `.nightshift/contracts/current/`
  - `.nightshift/contracts/history/`
- No dual-write between legacy and layered contract paths
- Existing callers should continue using `IssueRegistry` APIs without path knowledge

## Required Marker Extension

Extend the migration marker to support:

```yaml
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
contract_storage_source: layered
```

Rules:

- if `contract_storage_source` is absent:
  - contract storage remains compatibility mode
- if `contract_storage_source: layered`:
  - repository must already be in layered project config mode
- if `project_config_source: compatibility` and `contract_storage_source: layered`:
  - fail clearly

## Task Breakdown

### Task 1: Contract Storage Resolution Models

Add small resolution models for contract storage mode.

Suggested additions:

- extend `src/nightshift/config/models.py`
- add contract storage resolution helpers in `src/nightshift/config/loader.py`

Needed concepts:

- contract storage mode enum
- resolved contract storage paths

Recommended API:

- `resolve_contract_storage(repo_root: Path) -> ResolvedContractStorage`

### Task 2: IssueRegistry Contract Path Refactor

Refactor `IssueRegistry` so contract read/write paths come from the contract storage resolver instead of hardcoded legacy paths.

Expected behavior:

- `save_contract()`
- `get_contract()`
- `list_contracts()`
- `list_contract_revisions()`

must all honor the active contract storage mode.

Issue record paths remain unchanged in this slice.

### Task 3: Layered Contract Path Semantics

Support the new layered layout:

- current:
  - `.nightshift/contracts/current/<issue_id>.yaml`
- history:
  - `.nightshift/contracts/history/<issue_id>/<sequence>-<revision>.yaml`

Compatibility layout remains:

- current:
  - `nightshift/issues/<issue_id>.yaml`
- history:
  - `nightshift/contracts/<issue_id>/<sequence>-<revision>.yaml`

### Task 4: Migration Validation Rules

Add validation so invalid marker combinations fail clearly.

Required checks:

- unsupported `layout_version`
- `runtime_layout_source: layered` still rejected in current migration stage
- `contract_storage_source: layered` requires `project_config_source: layered`

### Task 5: Tests

Add or update tests for:

- compatibility repository contract writes stay in legacy paths
- layered contract repository writes current/history contracts in layered paths
- `get_contract()` resolves current contract correctly in both modes
- `list_contract_revisions()` resolves history correctly in both modes
- invalid marker combinations fail clearly

Likely files:

- `tests/test_config_loader.py`
- `tests/test_issue_registry.py`

### Task 6: Docs

Update docs to explain:

- compatibility vs layered contract storage
- marker extension for `contract_storage_source`
- Phase 2 still does not migrate records/runs

Likely files:

- `docs/architecture/product/contract-storage-migration.md`
- `docs/usage/configuration.md`
- possibly `docs/usage/workflow.md` if contract path wording needs adjustment

## Verification

Required verification:

```bash
./.venv/bin/python -m pytest tests/test_config_loader.py tests/test_issue_registry.py -q
./.venv/bin/python -m pytest -q
```

If any queue admission or work-order freeze behavior is touched indirectly, also run:

```bash
./.venv/bin/python -m pytest tests/test_queue_admission_service.py tests/test_queue_add_cli.py -q
```

## Suggested Implementation Order

1. extend marker schema and contract storage resolver
2. add tests for marker combinations
3. refactor `IssueRegistry` to use resolved paths
4. add layered/compatibility contract-path tests
5. update docs
6. run targeted and full verification

## Success Criteria

This slice is complete when:

- compatibility repositories behave exactly as before
- layered repositories can store current and revision contracts under `.nightshift/contracts/`
- no repository writes both legacy and layered contract paths as authoritative outputs
- invalid migration markers fail clearly
- docs describe the Phase 2 boundary without implying record/run migration is done
