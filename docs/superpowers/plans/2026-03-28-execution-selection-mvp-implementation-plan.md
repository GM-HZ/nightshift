# Execution Selection MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a product-layer execution-selection slice that can run a selected list of admitted local issues or all schedulable local issues by sequencing the existing kernel `run-one` primitive.

**Architecture:** Implement execution selection above the verified kernel without changing kernel run semantics. Add a product-layer batch selector and sequential runner that resolves a concrete batch from `IssueRegistry`, delegates each item to `RunOrchestrator.run_one()`, and returns an operator-friendly batch summary.

**Tech Stack:** Python, Typer CLI, Pydantic models, existing NightShift config/registry/orchestrator layers, product-layer execution-selection module

---

## File Map

### New Files

- `src/nightshift/product/execution_selection/__init__.py`
  Exports product-layer execution-selection helpers.
- `src/nightshift/product/execution_selection/models.py`
  Pydantic models for selection results, batch requests, per-issue results, and batch summaries.
- `src/nightshift/product/execution_selection/selector.py`
  Resolve explicit issue lists or `all` into a concrete schedulable batch.
- `src/nightshift/product/execution_selection/runner.py`
  Sequential fail-fast batch runner that delegates to `RunOrchestrator.run_one()`.
- `tests/test_execution_selection_selector.py`
  Selection-gate coverage for explicit ids, dedupe, and `run --all`.
- `tests/test_execution_selection_runner.py`
  Batch-runner coverage for sequential execution and fail-fast summaries.
- `tests/test_execution_selection_cli.py`
  CLI coverage for `run --issues` and `run --all`.

### Modified Files

- `src/nightshift/cli/app.py`
  Add `run` command above the existing `run-one` primitive.
- `docs/architecture/product/execution-selection-mvp.md`
  Sync implementation notes if needed.
- `docs/architecture/product/README.md`
  Note current implementation status after landing.
- `README.md`
  Update CLI surface and product-boundary notes once implemented.

---

## Task 1: Add Execution-Selection Product Models

**Files:**
- Create: `src/nightshift/product/execution_selection/__init__.py`
- Create: `src/nightshift/product/execution_selection/models.py`
- Test: `tests/test_execution_selection_selector.py`

- [ ] **Step 1: Write the failing model/selector tests**

Cover:
- explicit issue id list request shape
- deduped effective selection order
- empty explicit issue list rejection
- batch summary shape for later runner use

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_execution_selection_selector.py -v`
Expected: FAIL because execution-selection module does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- request/result models
- selection item model
- batch summary model

Keep the first version narrow and operator-facing.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_execution_selection_selector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/execution_selection/__init__.py src/nightshift/product/execution_selection/models.py tests/test_execution_selection_selector.py
git commit -m "feat: add execution selection models"
```

## Task 2: Implement Selection Gate

**Files:**
- Create: `src/nightshift/product/execution_selection/selector.py`
- Test: `tests/test_execution_selection_selector.py`

- [ ] **Step 1: Write the failing selector tests**

Cover:
- `run --issues` preserves first-seen explicit order while removing duplicates
- `run --issues` rejects unknown issue ids before starting
- `run --issues` rejects non-schedulable issue ids before starting
- `run --all` returns current schedulable issues in registry canonical order
- `run --all` returns an empty selection cleanly

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_execution_selection_selector.py -v`
Expected: FAIL because selector logic does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- `resolve_selected_issues(...)`
- `resolve_all_schedulable_issues(...)`

Rules:
- fail closed for explicit invalid requests
- no partial execution on explicit-selection errors
- reuse `IssueRegistry` current schedulable ordering for `all`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_execution_selection_selector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/execution_selection/selector.py tests/test_execution_selection_selector.py
git commit -m "feat: add execution selection gate"
```

## Task 3: Implement Sequential Fail-Fast Batch Runner

**Files:**
- Create: `src/nightshift/product/execution_selection/runner.py`
- Test: `tests/test_execution_selection_runner.py`

- [ ] **Step 1: Write the failing runner tests**

Cover:
- sequentially delegates each issue to the existing `run-one` primitive
- stops after first rejected/aborted/failure result
- reports accepted count and attempted count
- reports first failure issue id
- reports clean empty batch summary without invoking `run-one`

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_execution_selection_runner.py -v`
Expected: FAIL because runner does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- batch runner that accepts a callable or orchestrator dependency with `run_one(issue_id)`
- sequential fail-fast policy only
- small batch summary model

Do not add new persistence or new kernel state here.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_execution_selection_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/execution_selection/runner.py tests/test_execution_selection_runner.py
git commit -m "feat: add execution selection runner"
```

## Task 4: Add CLI `run --issues` and `run --all`

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_execution_selection_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Cover:
- `run --issues GH-1,GH-2` resolves config/repo and prints selected ids
- `run --all` uses registry ordering
- explicit invalid selection exits before any batch execution
- empty `run --all` exits cleanly with an operator-friendly message
- failure in one issue stops the batch and prints summary

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_execution_selection_cli.py -v`
Expected: FAIL because CLI command does not exist

- [ ] **Step 3: Write minimal implementation**

Add:
- `nightshift run --issues <csv>`
- `nightshift run --all`

Behavior:
- require exactly one of `--issues` or `--all`
- resolve repo from `--repo` or config
- call selector first
- call sequential runner second
- print immediate operator summary

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_execution_selection_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_execution_selection_cli.py
git commit -m "feat: add batch run command"
```

## Task 5: Sync Docs and CLI Surface

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/product/README.md`
- Modify: `docs/architecture/product/execution-selection-mvp.md`

- [ ] **Step 1: Update docs**

Reflect:
- `run` command now exists
- current policy is sequential fail-fast only
- `run --all` reuses current registry ordering
- daemon/continue-on-failure remain out of scope

- [ ] **Step 2: Commit**

```bash
git add README.md docs/architecture/product/README.md docs/architecture/product/execution-selection-mvp.md
git commit -m "docs: update execution selection status"
```

## Task 6: Final Verification

**Files:**
- Verify targeted tests
- Verify full suite

- [ ] **Step 1: Run targeted tests**

```bash
python -m pytest tests/test_execution_selection_selector.py tests/test_execution_selection_runner.py tests/test_execution_selection_cli.py -v
```

Expected: PASS

- [ ] **Step 2: Run full regression**

```bash
python -m pytest -v
```

Expected: PASS

- [ ] **Step 3: Record final outcome**

Summarize:
- what product behavior now exists
- what remains explicitly out of scope
- exact verification evidence

---

## Implementation Notes

- Keep execution-selection logic in a product-layer module; do not push it down into kernel modules.
- Reuse existing `IssueRegistry.list_schedulable_records()` ordering for `run --all`.
- Prefer injecting a small `run_one(issue_id)` dependency into the batch runner so tests stay lightweight.
- The first version should not invent a second historical reporting model; operator output can be immediate CLI summary only.
- Fail closed for explicit-selection errors before any batch starts.

## Verification Commands

Run these during implementation:

```bash
python -m pytest tests/test_execution_selection_selector.py -v
python -m pytest tests/test_execution_selection_runner.py -v
python -m pytest tests/test_execution_selection_cli.py -v
python -m pytest tests/test_execution_selection_selector.py tests/test_execution_selection_runner.py tests/test_execution_selection_cli.py -v
python -m pytest -v
```

## Expected Outcome

After this plan lands, NightShift product workflow should support:

- ingesting a GitHub issue into an admitted local issue
- running a human-selected batch of local issues
- running all currently schedulable local issues in canonical order
- stopping on first failure with a clear batch summary

What still remains after this slice:

- splitter-driven issue creation
- daemonized overnight loop
- continue-on-failure batch policy
- delivery automation / PR dispatch
- notifications and richer operator UX
