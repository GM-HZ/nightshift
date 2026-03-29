# Contract Context Field Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `non_goals` and `context_files` as first-class `IssueContract` fields so the frozen runtime contract preserves more of the approved execution context.

**Architecture:** Extend `IssueContract`, update Work Order materialization to project the fields into the contract, preserve them through normal contract persistence, and expose them lightly in `queue show`. Do not change orchestration, validation, or queue policy behavior in this pass.

**Tech Stack:** Python, Pydantic, existing NightShift contract/materialization flow, pytest, Typer CLI

---

## File Structure

### Modified files

- `src/nightshift/domain/contracts.py`
  Add `non_goals` and `context_files` to `IssueContract`.
- `src/nightshift/product/work_orders/materialize.py`
  Materialize the new fields from `Execution Work Order.execution`.
- `src/nightshift/registry/issue_registry.py`
  No behavior change expected, but persistence coverage should still pass with the expanded schema.
- `src/nightshift/cli/app.py`
  Extend `queue show` output to surface `non_goals_count` and `context_files`.
- `tests/test_domain_models.py`
  Contract schema and validation coverage.
- `tests/test_work_order_materialize.py`
  Materialization coverage for the new fields.
- `tests/test_issue_registry.py`
  Persistence round-trip coverage if needed.
- `tests/test_queue_add_cli.py`
  Ensure expanded contracts still behave under `queue add`.
- `tests/test_cli_smoke.py` or a new CLI test file as needed
  `queue show` output coverage.

### Design references

- `docs/architecture/product/contract-context-field-expansion.md`
- `docs/architecture/product/execution-work-order-materialization.md`
- `docs/architecture/product/execution-work-order-information-model.md`

## Task 1: Extend Contract Schema

**Files:**
- Modify: `src/nightshift/domain/contracts.py`
- Modify: `tests/test_domain_models.py`

- [ ] **Step 1: Write the failing contract tests**

Cover:

- `IssueContract` accepts `non_goals`
- `IssueContract` accepts `context_files`
- both fields are tuples of non-empty strings
- omission still behaves as intended if defaults are allowed, or required where execution contracts demand them

- [ ] **Step 2: Run the contract tests to verify failure**

Run:

```bash
python -m pytest tests/test_domain_models.py -v
```

Expected: FAIL because the schema does not yet expose the new fields.

- [ ] **Step 3: Extend `IssueContract`**

Add:

- `non_goals`
- `context_files`

Keep the fields frozen and typed consistently with the rest of the contract.

- [ ] **Step 4: Re-run the contract tests**

Run:

```bash
python -m pytest tests/test_domain_models.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/domain/contracts.py tests/test_domain_models.py
git commit -m "feat: add contract context fields"
```

## Task 2: Materialize Context Fields From Work Orders

**Files:**
- Modify: `src/nightshift/product/work_orders/materialize.py`
- Modify: `tests/test_work_order_materialize.py`

- [ ] **Step 1: Write the failing materialization tests**

Cover:

- `non_goals` are projected into `IssueContract`
- `context_files` are projected into `IssueContract`
- fields come only from Work Order execution input
- no project defaults are used to synthesize them

- [ ] **Step 2: Run the materialization tests to verify failure**

Run:

```bash
python -m pytest tests/test_work_order_materialize.py -v
```

Expected: FAIL because the materializer does not yet set the new fields.

- [ ] **Step 3: Update the materializer**

Project the validated Work Order fields directly into `IssueContract`.

- [ ] **Step 4: Re-run materialization tests**

Run:

```bash
python -m pytest tests/test_work_order_materialize.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/work_orders/materialize.py tests/test_work_order_materialize.py
git commit -m "feat: materialize contract context fields"
```

## Task 3: Confirm Persistence And Queue Admission Compatibility

**Files:**
- Modify if needed: `tests/test_issue_registry.py`
- Modify if needed: `tests/test_queue_admission_service.py`
- Modify if needed: `tests/test_queue_add_cli.py`

- [ ] **Step 1: Add regression tests where needed**

Cover:

- expanded contracts still persist and round-trip through `IssueRegistry`
- queue admission still freezes and writes contracts with the new fields

- [ ] **Step 2: Run persistence and queue tests**

Run:

```bash
python -m pytest tests/test_issue_registry.py tests/test_queue_admission_service.py tests/test_queue_add_cli.py -v
```

Expected: PASS after minimal compatibility updates.

- [ ] **Step 3: Make only compatibility fixes needed**

Do not change queue behavior. Only keep the expanded contract schema flowing through existing persistence/admission paths.

- [ ] **Step 4: Re-run the targeted tests**

Run:

```bash
python -m pytest tests/test_issue_registry.py tests/test_queue_admission_service.py tests/test_queue_add_cli.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_issue_registry.py tests/test_queue_admission_service.py tests/test_queue_add_cli.py
git commit -m "test: cover contract context field persistence"
```

## Task 4: Expose Light Visibility In `queue show`

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Modify or create: CLI test file covering `queue show`

- [ ] **Step 1: Write the failing CLI test**

Cover `queue show` output containing:

- `non_goals_count=<n>`
- `context_files=<comma-separated list>`

- [ ] **Step 2: Run the CLI test to verify failure**

Run:

```bash
python -m pytest tests/test_cli_smoke.py -v
```

Or, if a dedicated queue-show test file is added:

```bash
python -m pytest tests/<new-test-file>.py -v
```

- [ ] **Step 3: Update `queue show`**

Keep output concise. Do not dump full `non_goals`.

- [ ] **Step 4: Re-run the CLI test**

Run the same command as Step 2.

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests
git commit -m "feat: show contract context fields in queue output"
```

## Task 5: Docs And Final Verification

**Files:**
- Modify as needed:
  - `docs/architecture/product/contract-context-field-expansion.md`
  - `docs/usage/workflow.md`

- [ ] **Step 1: Update docs if implementation details differ slightly**

Keep the docs aligned with the final field names and `queue show` behavior.

- [ ] **Step 2: Run targeted tests**

Run:

```bash
python -m pytest \
  tests/test_domain_models.py \
  tests/test_work_order_materialize.py \
  tests/test_issue_registry.py \
  tests/test_queue_admission_service.py \
  tests/test_queue_add_cli.py -v
```

Expected: PASS

- [ ] **Step 3: Run full suite**

Run:

```bash
python -m pytest -q
```

Expected: PASS

- [ ] **Step 4: Final commit**

```bash
git add src tests docs
git commit -m "feat: expand contract context fields"
```
