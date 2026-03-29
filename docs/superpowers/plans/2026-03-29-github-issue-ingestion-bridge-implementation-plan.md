# GitHub Issue Ingestion Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a live GitHub issue planning-entry command that bridges into repository-local execution work orders without bypassing `queue add`.

**Architecture:** Add a small product-side ingestion bridge that fetches a GitHub issue, validates provenance and structured execution fields, maps it into the existing work-order model, and writes `.nightshift/work-orders/WO-<id>.md`. Keep `queue add` as the only contract freeze point and do not reintroduce direct issue-to-contract materialization.

**Tech Stack:** Python, Typer, existing NightShift config/product/work-order modules, pytest

---

## File Map

- Create: `src/nightshift/product/issue_ingestion_bridge/__init__.py`
- Create: `src/nightshift/product/issue_ingestion_bridge/models.py`
- Create: `src/nightshift/product/issue_ingestion_bridge/service.py`
- Create: `src/nightshift/product/issue_ingestion_bridge/github_client.py`
- Modify: `src/nightshift/product/work_orders/parser.py`
- Modify: `src/nightshift/product/work_orders/models.py`
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_issue_ingestion_bridge_service.py`
- Test: `tests/test_issue_ingestion_bridge_cli.py`
- Modify: `docs/usage/workflow.md`
- Modify: `README.md`

---

### Task 1: Define GitHub Ingestion Bridge Models

**Files:**
- Create: `src/nightshift/product/issue_ingestion_bridge/models.py`
- Create: `src/nightshift/product/issue_ingestion_bridge/__init__.py`
- Test: `tests/test_issue_ingestion_bridge_service.py`

- [ ] **Step 1: Write the failing model tests**

Add tests for:
- fetched GitHub issue payload shape used by the bridge
- validated structured execution fields extracted from a compliant issue
- work-order write summary returned by the bridge

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: FAIL because the bridge models do not exist yet

- [ ] **Step 3: Write minimal implementation**

Create frozen Pydantic models for:
- source GitHub issue payload
- normalized bridge input
- ingestion result summary

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/issue_ingestion_bridge/__init__.py src/nightshift/product/issue_ingestion_bridge/models.py tests/test_issue_ingestion_bridge_service.py
git commit -m "feat: add issue ingestion bridge models"
```

---

### Task 2: Implement Provenance And Admission Mapping

**Files:**
- Modify: `src/nightshift/product/issue_ingestion_bridge/service.py`
- Modify: `src/nightshift/product/work_orders/models.py`
- Test: `tests/test_issue_ingestion_bridge_service.py`

- [ ] **Step 1: Write the failing service tests**

Add tests for:
- provenance gate success
- allowlist failure
- missing label failure
- missing execution field failure
- mapping issue fields into work-order execution fields

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: FAIL because the bridge service is not implemented yet

- [ ] **Step 3: Write minimal implementation**

Implement a service that:
- accepts a fetched GitHub issue payload plus config
- validates author/label/template expectations
- maps structured fields into existing work-order frontmatter/body
- returns a write-ready work-order representation

Do not yet write files or call the network client in this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/issue_ingestion_bridge/service.py src/nightshift/product/work_orders/models.py tests/test_issue_ingestion_bridge_service.py
git commit -m "feat: add issue ingestion bridge service"
```

---

### Task 3: Add Work Order Write Path

**Files:**
- Modify: `src/nightshift/product/issue_ingestion_bridge/service.py`
- Modify: `src/nightshift/product/work_orders/parser.py`
- Test: `tests/test_issue_ingestion_bridge_service.py`

- [ ] **Step 1: Write the failing write-path tests**

Add tests for:
- compliant issue creates `.nightshift/work-orders/WO-<id>.md`
- existing work order rejects overwrite by default
- `--update-existing` path allows explicit replacement

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: FAIL because work-order write behavior is missing

- [ ] **Step 3: Write minimal implementation**

Implement:
- stable work-order id selection from the source issue
- write/update behavior for `.nightshift/work-orders/`
- operator-friendly duplicate/update guardrails

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/issue_ingestion_bridge/service.py src/nightshift/product/work_orders/parser.py tests/test_issue_ingestion_bridge_service.py
git commit -m "feat: write work orders from ingested issues"
```

---

### Task 4: Add GitHub Fetch Client

**Files:**
- Create: `src/nightshift/product/issue_ingestion_bridge/github_client.py`
- Test: `tests/test_issue_ingestion_bridge_service.py`

- [ ] **Step 1: Write the failing client tests**

Add tests for:
- token resolution from current environment conventions
- normalized issue fetch result shape
- operator-friendly errors for missing token or issue fetch failure

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: FAIL because the client does not exist yet

- [ ] **Step 3: Write minimal implementation**

Create a small client wrapper that:
- resolves token from supported environment variables
- fetches a single issue payload
- maps raw API shape into the bridge models

Keep the surface intentionally narrow.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/issue_ingestion_bridge/github_client.py tests/test_issue_ingestion_bridge_service.py
git commit -m "feat: add github issue bridge client"
```

---

### Task 5: Add `issue ingest-github` CLI

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_issue_ingestion_bridge_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Add tests for:
- happy-path `issue ingest-github`
- duplicate rejection without update flag
- `--update-existing`
- operator-friendly error output for missing token or invalid issue

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_cli.py -q`
Expected: FAIL because the CLI command does not exist yet

- [ ] **Step 3: Write minimal implementation**

Add a CLI command that:
- loads config and repo root using current helpers
- fetches the GitHub issue through the new client
- runs the bridge service
- writes the execution work order
- prints a short summary

Do not auto-run `queue add`.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_issue_ingestion_bridge_cli.py
git commit -m "feat: add github issue ingestion bridge cli"
```

---

### Task 6: Sync Docs

**Files:**
- Modify: `docs/usage/workflow.md`
- Modify: `README.md`

- [ ] **Step 1: Update workflow docs**

Explain the new planning bridge clearly:
- GitHub issue -> work order
- `queue add` remains the freeze point

- [ ] **Step 2: Update README**

Adjust current capability summary so GitHub issue ingestion is once again live, but as a bridge into work orders.

- [ ] **Step 3: Commit**

```bash
git add docs/usage/workflow.md README.md
git commit -m "docs: describe github issue ingestion bridge"
```

---

### Task 7: Final Verification

**Files:**
- Test: `tests/test_issue_ingestion_bridge_service.py`
- Test: `tests/test_issue_ingestion_bridge_cli.py`
- Test: regression suites around queue admission and work-order materialization

- [ ] **Step 1: Run focused ingestion tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_issue_ingestion_bridge_service.py tests/test_issue_ingestion_bridge_cli.py -q
```

Expected: PASS

- [ ] **Step 2: Run related regression coverage**

Run:

```bash
./.venv/bin/python -m pytest tests/test_queue_add_cli.py tests/test_work_order_parser.py tests/test_work_order_materialize.py tests/test_config_loader.py -q
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
git add README.md docs/usage/workflow.md src/nightshift/cli/app.py src/nightshift/product/issue_ingestion_bridge src/nightshift/product/work_orders tests/test_issue_ingestion_bridge_service.py tests/test_issue_ingestion_bridge_cli.py
git commit -m "test: verify github issue ingestion bridge"
```

