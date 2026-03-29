# Delivery Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a governed delivery path that turns an accepted execution result into a reviewable PR from a frozen accepted snapshot rather than the mutable current worktree.

**Architecture:** Extend acceptance handling to freeze a delivery snapshot under the accepted attempt artifacts, then add a product-side `deliver` command that consumes that snapshot, pushes the issue branch, opens a PR, and writes delivery linkage back to `IssueRecord`.

**Tech Stack:** Python, Typer, existing NightShift registry/state-store/orchestrator layers, git subprocess operations, GitHub API client, pytest

---

## File Map

- Create: `src/nightshift/product/delivery/__init__.py`
- Create: `src/nightshift/product/delivery/models.py`
- Create: `src/nightshift/product/delivery/service.py`
- Create: `src/nightshift/product/delivery/github_client.py`
- Modify: `src/nightshift/orchestrator/run_orchestrator.py`
- Modify: `src/nightshift/domain/records.py`
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_delivery_service.py`
- Test: `tests/test_delivery_cli.py`
- Modify: `README.md`
- Modify: `docs/usage/workflow.md`

---

### Task 1: Freeze Accepted Delivery Snapshot

**Files:**
- Modify: `src/nightshift/orchestrator/run_orchestrator.py`
- Test: `tests/test_run_orchestrator.py`

- [ ] Add failing tests for:
  - accepted attempt writes delivery snapshot artifact
  - accepted issue record moves to `delivery_state=branch_ready`
  - rejected/aborted attempts do not produce delivery snapshot
- [ ] Implement minimal accepted snapshot write under `.../delivery/`
- [ ] Record snapshot metadata sufficient for later delivery
- [ ] Run targeted tests and confirm green
- [ ] Commit

---

### Task 2: Add Delivery Models And Gate

**Files:**
- Create: `src/nightshift/product/delivery/models.py`
- Create: `src/nightshift/product/delivery/__init__.py`
- Test: `tests/test_delivery_service.py`

- [ ] Add failing tests for:
  - deliverability gate success
  - missing snapshot rejection
  - rejected/non-done issue rejection
- [ ] Implement minimal delivery request/result models
- [ ] Implement deliverability gate helpers
- [ ] Run targeted tests and confirm green
- [ ] Commit

---

### Task 3: Add Snapshot-Driven Delivery Service

**Files:**
- Create: `src/nightshift/product/delivery/service.py`
- Test: `tests/test_delivery_service.py`

- [ ] Add failing tests for:
  - load accepted snapshot and attempt/record linkage
  - push/create-PR success updates `IssueRecord`
  - delivery failure preserves `branch_ready`
- [ ] Implement service that:
  - loads accepted snapshot
  - prepares push/create-PR inputs from snapshot
  - updates delivery linkage on success
  - records failure cleanly without mutating accepted result
- [ ] Keep git/PR seams injectable for testability
- [ ] Run targeted tests and confirm green
- [ ] Commit

---

### Task 4: Add GitHub PR Client

**Files:**
- Create: `src/nightshift/product/delivery/github_client.py`
- Test: `tests/test_delivery_service.py`

- [ ] Add failing tests for:
  - token resolution
  - PR create request normalization
  - operator-friendly PR-create error surface
- [ ] Implement a narrow PR create client
- [ ] Reuse current GitHub token conventions first
- [ ] Run targeted tests and confirm green
- [ ] Commit

---

### Task 5: Add `deliver --issues`

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_delivery_cli.py`

- [ ] Add failing tests for:
  - happy-path `deliver --issues`
  - short error output for non-deliverable issue
  - PR-opened summary output
- [ ] Implement explicit `deliver --issues` CLI
- [ ] Keep `run --deliver` out of scope for this slice
- [ ] Run targeted tests and confirm green
- [ ] Commit

---

### Task 6: Sync Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/usage/workflow.md`

- [ ] Update docs so live flow becomes:
  - `issue ingest-github -> queue add -> run -> deliver`
- [ ] Keep richer delivery automation clearly out of scope
- [ ] Commit

---

### Task 7: Final Verification

- [ ] Run focused delivery + run-orchestrator regression tests
- [ ] Run full test suite: `./.venv/bin/python -m pytest -q`
- [ ] Push the branch after green verification

---

## Success Criteria

This plan is complete when:

- accepted attempts produce a frozen delivery snapshot
- `deliver --issues` is live
- delivery opens a PR from the accepted snapshot path
- `IssueRecord` delivery linkage is updated authoritatively
- current worktree drift is no longer the delivery source of truth
