# Queue Admission MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a product-layer queue-admission slice that gives operators an explicit `queue add` command for already-materialized local issues, while preserving the existing single live queue model and current kernel semantics.

**Architecture:** Implement queue admission above the verified kernel using the existing `IssueRegistry`, `IssueContract`, and `IssueRecord` models. `queue add` should validate that requested issues exist and are queue-admittable, optionally update `IssueRecord.queue_priority`, and fail closed without introducing a second queue store.

**Tech Stack:** Python, Typer CLI, Pydantic models, existing NightShift registry/config/CLI layers, product-layer queue-admission module

---

## File Map

### New Files

- `src/nightshift/product/queue_admission/__init__.py`
  Exports queue-admission helpers.
- `src/nightshift/product/queue_admission/models.py`
  Pydantic models for queue-admission requests, outcomes, per-issue statuses, and summaries.
- `src/nightshift/product/queue_admission/service.py`
  Validate explicit issue ids, enforce all-or-nothing admission, and perform idempotent queue admission.
- `tests/test_queue_admission_service.py`
  Queue-admission behavior coverage.
- `tests/test_queue_add_cli.py`
  CLI coverage for `queue add`.

### Modified Files

- `src/nightshift/cli/app.py`
  Add `queue add`.
- `docs/architecture/product/queue-admission-mvp.md`
  Sync implementation notes if needed.
- `docs/architecture/product/README.md`
  Note current implementation status after landing.
- `README.md`
  Update CLI surface and remaining-gap notes.

---

## Task 1: Add Queue-Admission Product Models

**Files:**
- Create: `src/nightshift/product/queue_admission/__init__.py`
- Create: `src/nightshift/product/queue_admission/models.py`
- Test: `tests/test_queue_admission_service.py`

- [ ] **Step 1: Write the failing model tests**

Cover:
- request shape for one or many explicit issue ids
- per-issue outcome shape
- all-or-nothing summary shape
- idempotent already-admitted status shape

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_queue_admission_service.py -v`
Expected: FAIL because queue-admission module does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- request/result models
- per-issue status model
- summary model

Keep models narrow and operator-facing.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_queue_admission_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/queue_admission/__init__.py src/nightshift/product/queue_admission/models.py tests/test_queue_admission_service.py
git commit -m "feat: add queue admission models"
```

## Task 2: Implement Queue-Admission Service

**Files:**
- Create: `src/nightshift/product/queue_admission/service.py`
- Test: `tests/test_queue_admission_service.py`

- [ ] **Step 1: Write the failing service tests**

Cover:
- `queue add GH-1` succeeds for `ready + pending`
- adding multiple issues succeeds when all are admissible
- duplicates collapse while preserving first-seen order
- `--priority` updates only `IssueRecord.queue_priority`
- contract priority remains unchanged
- already admitted `ready + pending` is treated as idempotent success
- unknown issue id fails closed
- missing contract fails closed
- missing record fails closed
- `running`, `done`, `blocked`, and `deferred` fail closed
- mixed-validity input performs no partial mutations

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_queue_admission_service.py -v`
Expected: FAIL because service logic does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- queue-admission validator and executor
- all-or-nothing validation before mutation
- idempotent handling for already-admitted issues

Rules:
- accepted initial state: `ready + pending`
- rejected states: `running`, `done`, `blocked`, `deferred`
- no second queue store
- no partial queue mutation on invalid requests

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_queue_admission_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/queue_admission/service.py tests/test_queue_admission_service.py
git commit -m "feat: add queue admission service"
```

## Task 3: Add CLI `queue add`

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_queue_add_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Cover:
- `queue add GH-1` succeeds and prints admitted status
- `queue add GH-1 GH-2` succeeds and prints both
- `queue add GH-1 --priority urgent` prints updated queue priority
- invalid admission exits with operator-friendly rejection
- mixed-validity explicit input exits without partial mutation

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_queue_add_cli.py -v`
Expected: FAIL because CLI command does not exist

- [ ] **Step 3: Write minimal implementation**

Add:
- `nightshift queue add <issue_id>...`
- optional `--priority`

Behavior:
- resolve repo from `--repo`
- delegate to queue-admission service
- print clear operator-facing result lines
- exit nonzero on fail-closed rejection

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_queue_add_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_queue_add_cli.py
git commit -m "feat: add queue admission command"
```

## Task 4: Align Ingestion UX With Queue Admission

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_issue_ingestion_cli.py`

- [ ] **Step 1: Write the failing ingestion UX tests**

Cover:
- default ingestion path remains queue-ready for current MVP fast path
- optional `--materialize-only` writes contract/record without auto-admission
- later `queue add` can admit the materialized issue

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_issue_ingestion_cli.py tests/test_queue_add_cli.py -v`
Expected: FAIL because `--materialize-only` and explicit queue-admission integration do not exist

- [ ] **Step 3: Write minimal implementation**

Add:
- `--materialize-only` on `issue ingest-github`

Behavior:
- default path preserves today’s fast path
- `--materialize-only` lands a local issue without declaring it queue-admitted in operator output
- queue admission remains explicit afterwards

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_issue_ingestion_cli.py tests/test_queue_add_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_issue_ingestion_cli.py tests/test_queue_add_cli.py
git commit -m "feat: separate materialization from queue admission"
```

## Task 5: Sync Docs and CLI Surface

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/product/README.md`
- Modify: `docs/architecture/product/queue-admission-mvp.md`

- [ ] **Step 1: Update docs**

Reflect:
- `queue add` now exists
- single live queue model is preserved
- `queue add` is all-or-nothing and idempotent for already-admitted issues
- `--materialize-only` review path exists if implemented in this slice

- [ ] **Step 2: Commit**

```bash
git add README.md docs/architecture/product/README.md docs/architecture/product/queue-admission-mvp.md
git commit -m "docs: update queue admission status"
```

## Task 6: Final Verification

**Files:**
- Verify targeted tests
- Verify full suite

- [ ] **Step 1: Run targeted tests**

```bash
python -m pytest tests/test_queue_admission_service.py tests/test_queue_add_cli.py tests/test_issue_ingestion_cli.py -v
```

Expected: PASS

- [ ] **Step 2: Run full regression**

```bash
python -m pytest -v
```

Expected: PASS

- [ ] **Step 3: Record final outcome**

Summarize:
- what operator queue workflow now exists
- what remains explicitly out of scope
- exact verification evidence

---

## Implementation Notes

- Keep queue-admission logic in a product-layer module; do not push it into kernel orchestration.
- Validate all requested issue ids before mutating any records.
- Reuse `IssueRegistry.get_contract()`, `get_record()`, `save_record()`, and existing reprioritization semantics.
- Do not introduce a new queue file or queue store.
- Treat `ready + pending` as idempotent success for `queue add`.
- Leave richer approval and scheduling policy for later product slices.

## Verification Commands

Run these during implementation:

```bash
python -m pytest tests/test_queue_admission_service.py -v
python -m pytest tests/test_queue_add_cli.py -v
python -m pytest tests/test_issue_ingestion_cli.py tests/test_queue_add_cli.py -v
python -m pytest tests/test_queue_admission_service.py tests/test_queue_add_cli.py tests/test_issue_ingestion_cli.py -v
python -m pytest -v
```

## Expected Outcome

After this plan lands, NightShift product workflow should support:

- ingesting a GitHub issue into a local issue
- explicitly admitting one or more local issues into the operator queue
- reprioritizing at admission time without mutating immutable contract priority
- running the admitted queue through `run --issues` or `run --all`

What still remains after this slice:

- splitter-driven issue creation
- proposal review UI
- daemonized overnight loop
- continue-on-failure scheduling policy
- delivery automation / PR dispatch
- notifications and richer operator UX
