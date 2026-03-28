# Issue Ingestion MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a product-layer GitHub issue ingestion slice that can validate provenance and admission, then materialize an execution-ready `IssueContract` and `IssueRecord` for the existing kernel to consume.

**Architecture:** Implement issue ingestion above the verified kernel without changing kernel execution semantics. Add a GitHub issue fetch and template parser, run provenance and admission gates, then write contracts and records through the existing registry interfaces.

**Tech Stack:** Python, Typer CLI, Pydantic models, existing NightShift registry/store/config layers, GitHub connector for issue fetch

---

## File Map

### New Files

- `src/nightshift/product/__init__.py`
  Product-layer package marker.
- `src/nightshift/product/issue_ingestion/__init__.py`
  Exports product-layer ingestion helpers.
- `src/nightshift/product/issue_ingestion/models.py`
  Pydantic models for parsed issue template data, provenance result, admission result, and materialization result.
- `src/nightshift/product/issue_ingestion/parser.py`
  Parse a GitHub issue title/body into a structured NightShift issue-template draft.
- `src/nightshift/product/issue_ingestion/provenance.py`
  Author allowlist, required label, and template-marker checks.
- `src/nightshift/product/issue_ingestion/admission.py`
  Execution-readiness checks and normalization into contract-ready data.
- `src/nightshift/product/issue_ingestion/materialize.py`
  Convert normalized ingestion data into `IssueContract` and `IssueRecord`.
- `tests/test_issue_ingestion_parser.py`
  Parser coverage.
- `tests/test_issue_ingestion_provenance.py`
  Provenance gate coverage.
- `tests/test_issue_ingestion_admission.py`
  Admission gate coverage.
- `tests/test_issue_ingestion_materialize.py`
  Materialization coverage.
- `tests/test_issue_ingestion_cli.py`
  End-to-end CLI coverage for `issue ingest-github`.

### Modified Files

- `src/nightshift/config/models.py`
  Add repository-local product ingestion config.
- `src/nightshift/config/loader.py`
  Validate new product config section.
- `src/nightshift/cli/app.py`
  Add `issue` CLI group and `issue ingest-github` command.
- `src/nightshift/domain/contracts.py`
  Only if needed for a small helper constructor or stricter normalization support.
- `src/nightshift/registry/issue_registry.py`
  Reuse existing `save_contract()` and `save_record()` paths, no behavior change expected unless a helper improves ergonomics.
- `src/nightshift/__init__.py`
  Only if package exports need a stable ingestion surface.
- `docs/architecture/product/issue-ingestion-mvp.md`
  Sync implementation notes or explicit MVP deviations if needed.

---

### Task 1: Add Product Ingestion Config

**Files:**
- Modify: `src/nightshift/config/models.py`
- Modify: `src/nightshift/config/loader.py`
- Test: `tests/test_config_loader.py`

- [ ] **Step 1: Write the failing config tests**

Add tests for:
- valid `product.issue_ingestion.allowed_authors`
- valid `product.issue_ingestion.required_label`
- rejection of blank authors or blank label

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config_loader.py -v`
Expected: FAIL because product ingestion config is unknown

- [ ] **Step 3: Write minimal implementation**

Add:
- `IssueIngestionConfig`
- `ProductConfig`
- `product: ProductConfig | None = None` on the root config model

Keep the first version minimal:
- `allowed_authors: list[str]`
- `required_label: str`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/config/models.py src/nightshift/config/loader.py tests/test_config_loader.py
git commit -m "feat: add issue ingestion config"
```

### Task 2: Parse NightShift GitHub Issue Template

**Files:**
- Create: `src/nightshift/product/__init__.py`
- Create: `src/nightshift/product/issue_ingestion/__init__.py`
- Create: `src/nightshift/product/issue_ingestion/models.py`
- Create: `src/nightshift/product/issue_ingestion/parser.py`
- Test: `tests/test_issue_ingestion_parser.py`

- [ ] **Step 1: Write the failing parser tests**

Cover:
- parsing issue title
- parsing template markers
- parsing `Goal`
- parsing `Allowed Paths`
- parsing `Acceptance Criteria`
- parsing `Verification Commands`
- graceful handling of missing sections

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_issue_ingestion_parser.py -v`
Expected: FAIL because parser module does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- `ParsedIssueTemplate`
- section parser using markdown headings and bullet extraction

Keep parsing deterministic and conservative. Do not add LLM inference here.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_issue_ingestion_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/__init__.py src/nightshift/product/issue_ingestion/__init__.py src/nightshift/product/issue_ingestion/models.py src/nightshift/product/issue_ingestion/parser.py tests/test_issue_ingestion_parser.py
git commit -m "feat: add issue template parser"
```

### Task 3: Implement Provenance Gate

**Files:**
- Create: `src/nightshift/product/issue_ingestion/provenance.py`
- Test: `tests/test_issue_ingestion_provenance.py`

- [ ] **Step 1: Write the failing provenance tests**

Cover:
- author allowlist pass
- author allowlist fail
- required label pass/fail
- template marker pass/fail
- structured rejection payload with explicit reasons

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_issue_ingestion_provenance.py -v`
Expected: FAIL because provenance gate does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- `ProvenanceResult`
- `check_provenance(issue, parsed_template, config)`

Rules:
- all three checks must pass
- return explicit failure reasons

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_issue_ingestion_provenance.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/issue_ingestion/provenance.py tests/test_issue_ingestion_provenance.py
git commit -m "feat: add issue provenance gate"
```

### Task 4: Implement Admission Gate

**Files:**
- Create: `src/nightshift/product/issue_ingestion/admission.py`
- Test: `tests/test_issue_ingestion_admission.py`

- [ ] **Step 1: Write the failing admission tests**

Cover:
- success when all execution fields exist
- rejection when `Goal` is missing
- rejection when `Allowed Paths` is empty
- rejection when `Acceptance Criteria` is empty
- rejection when `Verification Commands` is empty
- default resolution for priority and policy fields from `nightshift.yaml.issue_defaults`

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_issue_ingestion_admission.py -v`
Expected: FAIL because admission gate does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- `AdmissionResult`
- normalization output model for contract-ready data

Rules:
- never silently invent execution fields
- resolve defaults only from explicit repository config

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_issue_ingestion_admission.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/issue_ingestion/admission.py tests/test_issue_ingestion_admission.py
git commit -m "feat: add issue admission gate"
```

### Task 5: Materialize Contract And Record

**Files:**
- Create: `src/nightshift/product/issue_ingestion/materialize.py`
- Test: `tests/test_issue_ingestion_materialize.py`

- [ ] **Step 1: Write the failing materialization tests**

Cover:
- GitHub issue `#123` maps to local `GH-123`
- generated `IssueContract` is immutable and normalized
- generated `IssueRecord` starts as `ready/pending/none`
- queue priority initializes from contract priority
- conflicting existing contract content is rejected

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_issue_ingestion_materialize.py -v`
Expected: FAIL because materialization module does not exist

- [ ] **Step 3: Write minimal implementation**

Create:
- `materialize_issue(...)`
- deterministic local id mapping
- construction of `IssueContract`
- construction of `IssueRecord`
- persistence through `IssueRegistry.save_contract()` and `IssueRegistry.save_record()`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_issue_ingestion_materialize.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/issue_ingestion/materialize.py tests/test_issue_ingestion_materialize.py
git commit -m "feat: materialize ingested issues"
```

### Task 6: Add CLI Command

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_issue_ingestion_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Cover:
- `issue ingest-github --issue 1`
- success output includes local issue id and written paths
- provenance rejection returns non-zero with explicit reasons
- admission rejection returns non-zero with unresolved fields

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_issue_ingestion_cli.py -v`
Expected: FAIL because `issue` CLI group does not exist

- [ ] **Step 3: Write minimal implementation**

Add:
- `issue` Typer group
- `issue ingest-github` command
- GitHub issue fetch adapter boundary
- orchestration of parser -> provenance -> admission -> materialize

Keep command output structured and operator-readable.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_issue_ingestion_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_issue_ingestion_cli.py
git commit -m "feat: add github issue ingestion cli"
```

### Task 7: Wire CLI Help And Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/mvp-walkthrough.md`
- Modify: `docs/architecture/product/issue-ingestion-mvp.md`

- [ ] **Step 1: Write the failing docs expectations**

Record the expected user-facing command and boundary:
- this is product-layer ingestion
- it does not replace future splitter work
- it generates local contracts and records for the kernel

- [ ] **Step 2: Write minimal documentation updates**

Document:
- `issue ingest-github`
- provenance gate
- admission gate
- local `GH-<n>` mapping

- [ ] **Step 3: Sanity-check docs**

Run: `rg -n "issue ingest-github|GH-" README.md docs/mvp-walkthrough.md docs/architecture/product/issue-ingestion-mvp.md`
Expected: matches found in all relevant docs

- [ ] **Step 4: Commit**

```bash
git add README.md docs/mvp-walkthrough.md docs/architecture/product/issue-ingestion-mvp.md
git commit -m "docs: describe issue ingestion mvp"
```

### Task 8: Final Verification

**Files:**
- Verify: `tests/test_config_loader.py`
- Verify: `tests/test_issue_ingestion_parser.py`
- Verify: `tests/test_issue_ingestion_provenance.py`
- Verify: `tests/test_issue_ingestion_admission.py`
- Verify: `tests/test_issue_ingestion_materialize.py`
- Verify: `tests/test_issue_ingestion_cli.py`
- Verify: full suite

- [ ] **Step 1: Run targeted ingestion tests**

Run:

```bash
python -m pytest \
  tests/test_config_loader.py \
  tests/test_issue_ingestion_parser.py \
  tests/test_issue_ingestion_provenance.py \
  tests/test_issue_ingestion_admission.py \
  tests/test_issue_ingestion_materialize.py \
  tests/test_issue_ingestion_cli.py -v
```

Expected: PASS

- [ ] **Step 2: Run full suite**

Run:

```bash
python -m pytest -v
```

Expected: PASS

- [ ] **Step 3: Commit if docs-only or final fixes remain**

```bash
git add -A
git commit -m "chore: finalize issue ingestion mvp"
```

- [ ] **Step 4: Prepare review handoff**

Summarize:
- commands added
- config added
- gates enforced
- known non-goals retained
