# NightShift V4.2.1 Unified Spec

**Date:** 2026-03-27

**Status:** Patch revision over V4.2. V4.2.1 closes the implementation-critical ambiguities left in V4.2 around contract vs runtime boundaries, persistence source of truth, interface sufficiency, recovery semantics, splitter normalization, artifact layout, and phasing/report consistency.

**Normative inheritance rule:** V4.2.1 supersedes V4.2 where the two conflict. All unchanged V4.2 sections remain in force.

**Base spec:** `2026-03-27-nightshift-v4.2-unified-spec.md`

---

## 1. Scope Of The Patch

V4.2 already established the right architectural direction:

- split state domains
- stable kernel seams
- harness-owned validation
- isolated worktrees and rollback

The remaining problem was not product definition. It was execution ambiguity.

The highest-risk ambiguities that had to be closed before implementation were:

1. V4.2 still mixed contract fields and runtime state in places.
2. V4.2 did not define one clear persistent home for the current mutable `IssueRecord`.
3. V4.2 interface shapes were too thin for `recover`, reporting, and queue operations such as reprioritization.

Those primary seams in turn forced four follow-on clarifications:

4. recovery needed explicit rules for in-flight attempts after crash or restart
5. artifact directories needed to be separated from authoritative attempt records
6. splitter proposals needed a defined normalization pipeline into immutable issue contracts
7. the phasing story needed to separate a minimal kernel report from a richer report generator

V4.2.1 only tightens those seams. It does not broaden MVP scope.

---

## 2. Contract Boundary Closure

### 2.1 Canonical Contract Rule

`IssueContract` is an immutable, human-approved execution contract.

It stores:

- issue identity
- product intent
- execution policy
- validation requirements
- initial scheduling intent

It does **not** store mutable execution state.

### 2.2 Canonical Identifier Rule

The canonical contract identifier field is:

- `issue_id`

V4.2 examples that used `id` should be treated as legacy shorthand. V4.2.1 standardizes on `issue_id` across the unified spec, detailed design pack, persistence layout, and interfaces.

### 2.3 Fields Removed From The Contract

The following fields must not appear in `IssueContract`:

- `status`
- `issue_state`
- `attempt_state`
- `delivery_state`
- `blocker_type`
- `progress_type`
- `retry_count`
- `current_run_id`
- `latest_attempt_id`
- `accepted_attempt_id`
- `branch_name`
- `worktree_path`
- `last_attempt_summary`
- mutable queue metadata

These belong to `IssueRecord`, `AttemptRecord`, `RunState`, or delivery artifacts.

### 2.4 Priority Closure

V4.2 kept `priority` in the contract while also exposing queue reprioritization at the CLI.

V4.2.1 resolves this by splitting:

- `priority`
  Human-approved default scheduling intent stored in `IssueContract`
- `queue_priority`
  Current mutable scheduling value stored in `IssueRecord`

Operational rule:

- a new `IssueRecord.queue_priority` should default from `IssueContract.priority`
- `nightshift queue reprioritize <id>` mutates `queue_priority`
- queue operations must not rewrite the immutable contract

### 2.5 Contract Example

Suggested V4.2.1 execution issue schema:

```yaml
issue_id: NS-123
title: Fix cache invalidation race in session store
kind: execution
priority: high
engine_preferences:
  primary: codex
  fallback: claude_code
goal: Prevent stale session reads after invalidation under concurrent access.
description: >
  Existing invalidation logic allows stale reads under concurrent access.
acceptance:
  - deterministic invalidation test passes
  - core regression suite passes
allowed_paths:
  - src/session/
  - tests/session/
forbidden_paths:
  - migrations/
  - infra/
verification:
  issue_validation:
    required: true
    commands:
      - pytest tests/session/test_invalidation.py -q
    pass_condition:
      type: exit_code
      expected: 0
  static_validation:
    required: false
    commands:
      - ruff check src/session tests/session
      - mypy src/session
    pass_condition:
      type: all_exit_codes_zero
  regression_validation:
    required: true
    commands:
      - pytest tests/session/test_smoke.py -q
      - pytest tests/api/test_login.py -q
    pass_condition:
      type: all_exit_codes_zero
  promotion_validation:
    required: false
    commands: []
    pass_condition: null
test_edit_policy:
  can_add_tests: true
  can_modify_existing_tests: true
  can_weaken_assertions: false
  requires_test_change_reason: true
attempt_limits:
  max_files_changed: 3
  max_lines_added: 80
  max_lines_deleted: 40
timeouts:
  command_seconds: 600
  issue_budget_seconds: 3600
risk: medium
notes: Reproduce and fix only the invalidation race; do not redesign the storage backend.
```

Required contract fields:

- `issue_id`
- `title`
- `kind`
- `priority`
- `goal`
- `allowed_paths`
- `forbidden_paths`
- `verification`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`

---

## 3. Runtime State Closure

### 3.1 Mutable Runtime State Lives In Records

NightShift must keep runtime state outside the contract and in mutable runtime records:

- `IssueRecord`
  Current issue lifecycle, queue, and delivery-facing state
- `AttemptRecord`
  One concrete execution attempt
- `RunState`
  One overnight run

### 3.2 Current-State Rule

For every `issue_id`, there must be exactly one authoritative current `IssueRecord`.

That record owns:

- `issue_state`
- `attempt_state`
- `delivery_state`
- delivery linkage
- `blocker_type`
- `progress_type`
- `queue_priority`
- run linkage
- accepted branch linkage
- retry counters
- latest summary

### 3.3 Denormalized Run Snapshots Rule

Run-scoped issue snapshots may be retained inside a run artifact directory for auditability and reporting, but they are denormalized copies.

They are not the source of truth for the current issue state after the run finishes.

---

## 4. Persistence Closure

### 4.1 Persistence Domains

NightShift persistence now splits cleanly into three domains:

1. **Static project-controlled inputs**
   Immutable or intentionally edited by humans.
2. **Current mutable runtime snapshots**
   The latest authoritative state used by the harness.
3. **Run-scoped history**
   Attempts, events, reports, and audit artifacts.

### 4.2 Source Of Truth Rule

The authoritative store for current issue lifecycle state is:

- `IssueRecord`

The authoritative store for run and attempt history is:

- `RunState`
- `AttemptRecord`
- append-only event log
- alert history

This means the harness must never infer the current queue from old run folders alone.

### 4.3 Run Identifier Rule

`run_id` must be globally unique and must be used directly as the run directory name.

Recommended format:

```text
run-<UTC timestamp>-<short unique suffix>
```

Example:

```text
run-20260327T140500Z-01JQ8J7M6Q0P
```

Operational rule:

- a calendar date may appear inside the `run_id`
- a bare date must not be the `run_id`
- `nightshift recover --run <run-id>` and `nightshift report --run <run-id>` must address the exact unique run identifier

### 4.4 Recommended Persistence Layout

```text
nightshift/
  config.yaml
  issues/
    <issue_id>.yaml
  engines/
    codex.md
    claude_code.md
nightshift-data/
  issue-records/
    <issue_id>.json
  active-run.json
  alerts.ndjson
  runs/
    <run_id>/
      run-state.json
      events.ndjson
      report.md
      issues/
        <issue_id>.json
      attempts/
        <attempt_id>.json
      artifacts/
        attempts/
          <attempt_id>/
.nightshift/
  worktrees/
    issue-<issue_id>/
```

Rules:

- `nightshift/issues/<issue_id>.yaml` stores immutable `IssueContract`
- `nightshift-data/issue-records/<issue_id>.json` stores the authoritative current `IssueRecord`
- `nightshift-data/runs/<run_id>/...` stores run-scoped snapshots and history
- `active-run.json` stores the currently active run id if one exists

---

## 5. Kernel Interface Closure

### 5.1 Ownership Rule

The kernel interface boundary must now match the persistence boundary.

- `Issue Registry`
  Owns immutable contracts plus current mutable `IssueRecord` snapshots
- `State Store`
  Owns run state, attempt records, event history, and alert history

The Orchestrator must not bypass these interfaces and read or patch persistence files directly.

### 5.2 Minimum Interface Sufficiency Rule

The stable kernel interfaces must be rich enough to support:

- queue inspection
- queue reprioritization
- run recovery
- attempt inspection
- report generation
- audit log replay

At minimum, the detailed design pack must define:

- how to load and save full `IssueRecord`
- how to load and enumerate `AttemptRecord`
- how to load run-scoped issue snapshots for reporting
- how to enumerate runs
- how to read event history
- how to read alert history
- how to track the active run id
- how delivery linkage is stored on the current issue record

### 5.3 Reporting And Recovery Consequence

With this split:

- queue and current issue views read from the `Issue Registry`
- run reports and audit tools read from targeted run history in the `State Store`
- recovery targets a source run id but returns a new controlling run with a new `run_id`
- recovery uses both current issue records and the targeted run history

---

## 6. CLI Consequences

V4.2.1 does not add new CLI categories, but it tightens command meaning.

### 6.1 `queue reprioritize`

`nightshift queue reprioritize <id>` updates:

- `IssueRecord.queue_priority`

It must not mutate:

- `IssueContract.priority`

### 6.2 `queue show`

`nightshift queue show <id>` should display both:

- contract `priority`
- effective `queue_priority`

when they differ.

### 6.3 `recover` And `report`

`nightshift recover --run <run-id>` and `nightshift report --run <run-id>` must use the exact unique `run_id`, not a date alias.

Operational rule:

- `report --run <run-id>` reads the targeted run's persisted history, not current live queue state
- `recover --run <run-id>` treats the supplied `run_id` as the interrupted source run and creates a new controlling recovery run with a new `run_id`

---

## 7. Detailed Design Pack Composition

V4.2.1 includes a patch-level detailed design pack:

- revised:
  - `01-domain-model.md`
  - `02-kernel-interfaces.md`
  - `03-state-machines.md`
  - `04-engine-adapters-and-workspaces.md`
  - `05-requirement-splitter-and-context-loading.md`
  - `06-cli-config-persistence-alerting.md`
  - `07-language-and-phasing.md`

The pack README makes the V4.2.1 revision scope explicit so implementers do not need to guess which documents changed.

---

## 8. Migration Notes From V4.2

To upgrade an implementation target from V4.2 to V4.2.1:

1. Rename contract identifier fields from `id` to `issue_id`.
2. Remove runtime fields from issue contracts.
3. Introduce `IssueRecord.queue_priority` as mutable queue metadata.
4. Persist current issue records outside run folders.
5. Change run folder naming to exact unique `run_id` values.
6. Expand kernel interfaces so recovery and reporting do not require direct file access.
7. Add canonical config defaults for contract normalization.
8. Persist delivery linkage on the issue record rather than only in ad-hoc delivery outputs.

---

## 9. V4.2.1 Summary

NightShift V4.2.1 does not redefine the product.

It closes the implementation seams that remained too loose in V4.2:

- immutable contracts are now cleanly separated from mutable runtime state
- current issue truth is now stored independently from run history
- kernel interfaces are now sufficient for queue operations, recovery, and reporting

This makes V4.2.1 a better implementation target than V4.2 without expanding MVP scope.
