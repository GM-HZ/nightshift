# Product Run Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a minimal product-facing execution surface by adding `nightshift run --issues` and `nightshift run --all` on top of the existing frozen-contract and `run-one` kernel flow.

**Architecture:** Add a thin product-side batch runner that selects already-admitted issues and invokes the existing `RunOrchestrator.run_one()` sequentially. Keep the first version fail-fast and summary-oriented, with no new state machine and no reintroduction of ingestion, splitter, or delivery.

**Tech Stack:** Python, Typer, pytest, existing NightShift domain/registry/orchestrator modules

---

## File Map

- Create: `src/nightshift/product/execution_selection/__init__.py`
- Create: `src/nightshift/product/execution_selection/models.py`
- Create: `src/nightshift/product/execution_selection/service.py`
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_execution_selection_service.py`
- Test: `tests/test_execution_selection_cli.py`
- Modify: `docs/usage/workflow.md`
- Modify: `README.md`

---

### Task 1: Add Batch Execution Models

**Files:**
- Create: `src/nightshift/product/execution_selection/models.py`
- Create: `src/nightshift/product/execution_selection/__init__.py`
- Test: `tests/test_execution_selection_service.py`

- [ ] **Step 1: Write the failing model tests**

Add tests for:
- a batch request carrying ordered issue ids
- a batch summary carrying requested count, completed count, stopped_early, and last issue/run identifiers

- [ ] **Step 2: Run the targeted tests to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_execution_selection_service.py -q`
Expected: FAIL because the execution selection models do not exist yet

- [ ] **Step 3: Implement minimal batch models**

Create focused models for:
- explicit selection requests
- `run --all` selection summary
- final batch execution summary

Keep the model surface small and avoid future-policy knobs.

- [ ] **Step 4: Run the targeted tests to verify pass**

Run: `./.venv/bin/python -m pytest tests/test_execution_selection_service.py -q`
Expected: PASS for the new model-focused tests

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/execution_selection/__init__.py src/nightshift/product/execution_selection/models.py tests/test_execution_selection_service.py
git commit -m "feat: add execution selection models"
```

---

### Task 2: Add Sequential Fail-Fast Batch Service

**Files:**
- Modify: `src/nightshift/product/execution_selection/service.py`
- Test: `tests/test_execution_selection_service.py`

- [ ] **Step 1: Write the failing service tests**

Add tests for:
- explicit issue list execution in caller-supplied order
- `run_all` execution using registry schedulable ordering
- fail-fast stop on first rejected/failed issue
- summary counts and stopped-early behavior

- [ ] **Step 2: Run the targeted tests to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_execution_selection_service.py -q`
Expected: FAIL because the batch service is not implemented yet

- [ ] **Step 3: Implement the minimal batch service**

Create a service that:
- accepts a prepared `RunOrchestrator`
- resolves issue ids either explicitly or from `IssueRegistry.list_schedulable_records()`
- calls `run_one()` sequentially
- stops on first non-accepted result
- returns a lightweight batch summary

Do not add:
- continue-on-failure
- concurrency
- delivery hooks

- [ ] **Step 4: Run the targeted tests to verify pass**

Run: `./.venv/bin/python -m pytest tests/test_execution_selection_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/execution_selection/service.py tests/test_execution_selection_service.py
git commit -m "feat: add fail-fast batch execution service"
```

---

### Task 3: Add `run --issues` And `run --all` CLI Commands

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_execution_selection_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Add tests for:
- `nightshift run --issues A,B`
- `nightshift run --all`
- fail-fast batch output
- operator-friendly error handling for malformed input or missing config

- [ ] **Step 2: Run the targeted tests to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_execution_selection_cli.py -q`
Expected: FAIL because the `run` command group does not exist yet

- [ ] **Step 3: Implement the CLI wiring**

Add a product-facing `run` command group or equivalent command shape that:
- loads config the same way current commands do
- resolves repo root the same way current commands do
- builds the existing orchestrator
- calls the new batch service
- emits short summary output

Do not remove `run-one`.

- [ ] **Step 4: Run the targeted tests to verify pass**

Run: `./.venv/bin/python -m pytest tests/test_execution_selection_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_execution_selection_cli.py
git commit -m "feat: add product run commands"
```

---

### Task 4: Sync Docs To The Restored Run Surface

**Files:**
- Modify: `docs/usage/workflow.md`
- Modify: `README.md`

- [ ] **Step 1: Update the usage docs**

Update:
- current operator flow
- command examples
- distinction between `run-one` and product-facing `run`

- [ ] **Step 2: Update the top-level README**

Adjust the “What Works Today” and quick capability summary so it reflects the restored run surface.

- [ ] **Step 3: Review doc wording for truthfulness**

Confirm that docs:
- claim only what the live code now supports
- still distinguish live product surface from broader design direction

- [ ] **Step 4: Commit**

```bash
git add docs/usage/workflow.md README.md
git commit -m "docs: describe restored product run surface"
```

---

### Task 5: Final Verification

**Files:**
- Test: `tests/test_execution_selection_service.py`
- Test: `tests/test_execution_selection_cli.py`
- Test: existing regression suites touched by CLI/orchestrator wiring

- [ ] **Step 1: Run focused product execution tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_execution_selection_service.py tests/test_execution_selection_cli.py -q
```

Expected: PASS

- [ ] **Step 2: Run broader regression coverage**

Run:

```bash
./.venv/bin/python -m pytest tests/test_queue_add_cli.py tests/test_run_orchestrator.py tests/test_config_loader.py -q
```

Expected: PASS

- [ ] **Step 3: Run full suite**

Run:

```bash
./.venv/bin/python -m pytest -q
```

Expected: PASS

- [ ] **Step 4: Commit final verification state**

```bash
git add README.md docs/usage/workflow.md src/nightshift/cli/app.py src/nightshift/product/execution_selection tests/test_execution_selection_service.py tests/test_execution_selection_cli.py
git commit -m "test: verify product run surface"
```

