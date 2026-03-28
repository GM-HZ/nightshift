# Splitter And Proposal Review MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first upstream planning slice above issue ingestion: accept a requirement document, generate structured `SplitterProposal` review artifacts, let a human approve them, and publish approved proposals as standard NightShift GitHub issues that the existing ingestion path can consume.

**Architecture:** Implement splitter/proposal review strictly in the product layer. The splitter must not emit final immutable contracts directly. It should persist proposals locally, track explicit review state, and publish only approved proposals into standard NightShift GitHub issue bodies that satisfy existing ingestion provenance and admission expectations.

**Tech Stack:** Python, Typer CLI, Pydantic models, local proposal persistence under `nightshift-data/`, GitHub publishing boundary, existing product issue-ingestion template conventions

---

## File Map

### New Files

- `src/nightshift/product/splitter/__init__.py`
  Exports proposal models and review/publish helpers.
- `src/nightshift/product/splitter/models.py`
  Pydantic models for proposal batches, proposals, review state, and publish results.
- `src/nightshift/product/splitter/storage.py`
  Read/write proposal review artifacts under `nightshift-data/proposals/`.
- `src/nightshift/product/splitter/review.py`
  Proposal review transitions such as approve/reject/edit-ready validation.
- `src/nightshift/product/splitter/github_publish.py`
  Render approved proposals into standard NightShift GitHub issue template bodies and publish them.
- `tests/test_splitter_storage.py`
  Proposal persistence coverage.
- `tests/test_splitter_review.py`
  Review-state transition coverage.
- `tests/test_splitter_publish.py`
  Publishing/rendering coverage.
- `tests/test_splitter_cli.py`
  CLI coverage for `split`, `proposals show`, and `proposals publish`.

### Modified Files

- `src/nightshift/cli/app.py`
  Add `split` and `proposals` command groups.
- `docs/architecture/product/splitter-proposal-review-mvp.md`
  Sync implementation notes if needed.
- `docs/architecture/product/README.md`
  Note current implementation status after landing.
- `README.md`
  Update current CLI surface and remaining-gap notes.

---

## Task 1: Add Proposal Models And Local Persistence

**Files:**
- Create: `src/nightshift/product/splitter/__init__.py`
- Create: `src/nightshift/product/splitter/models.py`
- Create: `src/nightshift/product/splitter/storage.py`
- Test: `tests/test_splitter_storage.py`

- [ ] **Step 1: Write the failing storage tests**

Cover:
- proposal batch model with one or more proposals
- proposal review state defaults to pending review
- persistence under `nightshift-data/proposals/`
- loading saved proposal batches back into typed models
- duplicate save/update behavior is explicit and safe

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_splitter_storage.py -v`
Expected: FAIL because splitter storage does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- `SplitterProposal`
- `ProposalBatch`
- `ProposalReviewState`
- storage helpers for save/load/list

Keep persistence file-based and auditable.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_splitter_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/splitter/__init__.py src/nightshift/product/splitter/models.py src/nightshift/product/splitter/storage.py tests/test_splitter_storage.py
git commit -m "feat: add splitter proposal storage"
```

## Task 2: Add Review-State Transitions

**Files:**
- Create: `src/nightshift/product/splitter/review.py`
- Test: `tests/test_splitter_review.py`

- [ ] **Step 1: Write the failing review tests**

Cover:
- approve proposal
- reject proposal
- prohibit publish when proposal remains pending
- prohibit publish when approved proposal is missing required execution fields
- allow edited proposals to remain reviewable and publishable after validation

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_splitter_review.py -v`
Expected: FAIL because review logic does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- explicit review status transitions
- validation helper for publish-readiness

Rules:
- approval must be explicit
- publish must fail closed if required fields are unresolved
- no silent guessing

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_splitter_review.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/splitter/review.py tests/test_splitter_review.py
git commit -m "feat: add proposal review transitions"
```

## Task 3: Add GitHub Issue Rendering And Publish Boundary

**Files:**
- Create: `src/nightshift/product/splitter/github_publish.py`
- Test: `tests/test_splitter_publish.py`

- [ ] **Step 1: Write the failing publish tests**

Cover:
- approved proposal renders into the standard NightShift GitHub issue template
- rendered issue includes required provenance markers
- rendered issue includes `Goal`, `Allowed Paths`, `Acceptance Criteria`, and `Verification Commands`
- duplicate publish attempts are rejected
- unapproved proposals cannot publish

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_splitter_publish.py -v`
Expected: FAIL because publish boundary does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- proposal-to-issue-body renderer
- publish wrapper that records published status locally

Important first-version boundary:
- keep GitHub create call behind a small adapter seam
- tests should use a fake publisher callable

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_splitter_publish.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/splitter/github_publish.py tests/test_splitter_publish.py
git commit -m "feat: add proposal publish boundary"
```

## Task 4: Add Minimal CLI Flow

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_splitter_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Cover:
- `split --file requirements/foo.md` creates a proposal batch
- `proposals show` lists saved proposal ids and statuses
- `proposals publish PROP-1` publishes only explicitly approved proposals
- operator-friendly errors for unapproved or incomplete proposals

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_splitter_cli.py -v`
Expected: FAIL because CLI does not exist

- [ ] **Step 3: Write minimal implementation**

Add:
- `nightshift split --file ...`
- `nightshift proposals show`
- `nightshift proposals publish ...`

Implementation note:
- the first splitter implementation may use a deterministic stub/skill adapter boundary rather than a full intelligent decomposition engine
- the important product behavior is proposal persistence and review/publish workflow

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_splitter_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_splitter_cli.py
git commit -m "feat: add splitter proposal CLI"
```

## Task 5: Integrate With Existing Ingestion Contract

**Files:**
- Modify: `tests/test_issue_ingestion_cli.py` only if needed for end-to-end shape confirmation
- Possibly modify docs examples

- [ ] **Step 1: Add a narrow integration test**

Cover:
- a published proposal renders into a GitHub issue body that is acceptable to the current `issue ingest-github` parser and admission flow

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_splitter_publish.py tests/test_issue_ingestion_cli.py -v`
Expected: FAIL if shape mismatch exists

- [ ] **Step 3: Write minimal implementation**

Adjust proposal rendering until published issue shape matches the existing ingestion contract exactly.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_splitter_publish.py tests/test_issue_ingestion_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/splitter tests/test_splitter_publish.py tests/test_issue_ingestion_cli.py
git commit -m "fix: align proposal publish shape with issue ingestion"
```

## Task 6: Sync Docs And CLI Surface

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/product/README.md`
- Modify: `docs/architecture/product/splitter-proposal-review-mvp.md`

- [ ] **Step 1: Update docs**

Reflect:
- proposal review artifacts now exist
- approved proposals publish to standard NightShift GitHub issues
- full autonomous planning is still out of scope

- [ ] **Step 2: Commit**

```bash
git add README.md docs/architecture/product/README.md docs/architecture/product/splitter-proposal-review-mvp.md
git commit -m "docs: update splitter proposal review status"
```

## Task 7: Final Verification

**Files:**
- Verify targeted tests
- Verify full suite

- [ ] **Step 1: Run targeted tests**

```bash
python -m pytest tests/test_splitter_storage.py tests/test_splitter_review.py tests/test_splitter_publish.py tests/test_splitter_cli.py -v
```

Expected: PASS

- [ ] **Step 2: Run cross-slice verification**

```bash
python -m pytest tests/test_splitter_publish.py tests/test_issue_ingestion_cli.py tests/test_queue_add_cli.py tests/test_execution_selection_cli.py -v
```

Expected: PASS

- [ ] **Step 3: Run full regression**

```bash
python -m pytest -v
```

Expected: PASS

- [ ] **Step 4: Record final outcome**

Summarize:
- what planning workflow now exists
- what still requires human review
- exact verification evidence

---

## Implementation Notes

- Keep splitter/proposal review firmly above issue ingestion; do not directly write final contracts from this slice.
- Use GitHub issues as the durable product handoff between planning and execution.
- The first splitter implementation may be deterministic or skill-backed, as long as proposal persistence and human review remain explicit.
- Proposal publish should be adapter-backed so the GitHub create call can be swapped or mocked cleanly.
- Persist review artifacts locally before publication; do not hide proposal state in transient memory.

## Verification Commands

Run these during implementation:

```bash
python -m pytest tests/test_splitter_storage.py -v
python -m pytest tests/test_splitter_review.py -v
python -m pytest tests/test_splitter_publish.py -v
python -m pytest tests/test_splitter_cli.py -v
python -m pytest tests/test_splitter_publish.py tests/test_issue_ingestion_cli.py -v
python -m pytest tests/test_splitter_storage.py tests/test_splitter_review.py tests/test_splitter_publish.py tests/test_splitter_cli.py -v
python -m pytest -v
```

## Expected Outcome

After this plan lands, NightShift product workflow should support:

- reading a requirement file
- producing structured proposal review artifacts
- explicitly approving proposals
- publishing approved proposals as standard NightShift GitHub issues
- feeding those issues into the already-implemented ingestion, queue-admission, and execution flow

What still remains after this slice:

- sophisticated requirement decomposition quality improvements
- richer review UI
- fully autonomous planning approval
- delivery automation / PR dispatch
- merge automation and notifications
