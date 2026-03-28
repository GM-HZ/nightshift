# Delivery / PR Dispatcher MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the smallest product-layer delivery flow that can take an already accepted NightShift issue, push its branch, create a GitHub PR, and record delivery linkage.

**Architecture:** Build delivery as a product-layer service on top of existing accepted worktree state, not as a kernel concern. Reuse the existing `IssueRegistry` delivery linkage seam, add explicit delivery config and CLI entrypoints, and keep `run --deliver` as a thin convenience wrapper around the same underlying delivery action used by `deliver`.

**Tech Stack:** Python, Typer CLI, Git subprocess wrappers, existing GitHub adapter patterns, pytest

---

### Task 1: Add Delivery Config And Domain Models

**Files:**
- Modify: `src/nightshift/config/models.py`
- Create: `src/nightshift/product/delivery/models.py`
- Test: `tests/test_delivery_models.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_delivery_config_defaults():
    config = NightShiftConfig.model_validate({"project": {"repo_path": "/tmp/repo"}})
    assert config.product.delivery.remote_name == "origin"
    assert config.product.delivery.base_branch == "master"


def test_delivery_request_requires_issue_ids():
    with pytest.raises(ValueError):
        DeliveryRequest(issue_ids=[])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_models.py -v`
Expected: FAIL because delivery config/models do not exist yet

- [ ] **Step 3: Write minimal implementation**

Add:
- product delivery config under `NightShiftConfig`
- `DeliveryRequest`
- `DeliveryResult`
- `DeliveryBatchResult`
- any minimal enums or literals needed for delivery state handling

- [ ] **Step 4: Run tests to verify they pass**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/config/models.py src/nightshift/product/delivery/models.py tests/test_delivery_models.py
git commit -m "feat: add delivery config and models"
```

### Task 2: Add Deliverability Gate

**Files:**
- Create: `src/nightshift/product/delivery/admission.py`
- Test: `tests/test_delivery_admission.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_admission_accepts_done_and_accepted_issue(tmp_path):
    ...
    result = evaluate_deliverability(contract, record)
    assert result.allowed is True


def test_admission_rejects_non_accepted_issue(tmp_path):
    ...
    assert result.allowed is False
    assert "accepted" in result.reason


def test_admission_rejects_issue_with_existing_delivery_ref(tmp_path):
    ...
    assert result.allowed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_admission.py -v`
Expected: FAIL because delivery admission logic does not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement a delivery gate that checks:
- `issue_state == done`
- `attempt_state == accepted`
- `branch_name` present
- `worktree_path` present and exists
- existing `delivery_ref` causes failure in MVP

- [ ] **Step 4: Run tests to verify they pass**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_admission.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/delivery/admission.py tests/test_delivery_admission.py
git commit -m "feat: add delivery admission gate"
```

### Task 3: Add Git And PR Rendering Seams

**Files:**
- Create: `src/nightshift/product/delivery/git_ops.py`
- Create: `src/nightshift/product/delivery/github_pr.py`
- Test: `tests/test_delivery_rendering.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_commit_message_renders_from_issue_id_and_title():
    message = render_commit_message(issue_id="GH-7", title="增加中文 README 说明")
    assert "GH-7" in message


def test_pr_payload_contains_issue_title_and_verification_commands():
    payload = render_pr_payload(...)
    assert "Verification" in payload.body
    assert "README.zh-CN.md" in payload.body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_rendering.py -v`
Expected: FAIL because rendering and delivery seams do not exist yet

- [ ] **Step 3: Write minimal implementation**

Add:
- commit message renderer
- PR title/body renderer
- git operation seam functions for add/commit/push
- GitHub PR create seam that mirrors existing adapter style

- [ ] **Step 4: Run tests to verify they pass**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_rendering.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/delivery/git_ops.py src/nightshift/product/delivery/github_pr.py tests/test_delivery_rendering.py
git commit -m "feat: add delivery git and pr rendering seams"
```

### Task 4: Add Delivery Service

**Files:**
- Create: `src/nightshift/product/delivery/service.py`
- Test: `tests/test_delivery_service.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_service_delivers_single_accepted_issue_and_updates_registry(tmp_path):
    ...
    result = service.deliver(request)
    assert result.delivered == ["GH-7"]
    updated = registry.get_record("GH-7")
    assert updated.delivery_state == "submitted"
    assert updated.delivery_ref == "https://github.com/GM-HZ/nightshift/pull/123"


def test_service_marks_failed_when_push_fails(tmp_path):
    ...
    assert result.failed == ["GH-7"]
    assert registry.get_record("GH-7").delivery_state == "failed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_service.py -v`
Expected: FAIL because service orchestration does not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement service flow:
- load contract/record
- run delivery admission
- stage and commit accepted worktree changes
- push branch
- create PR
- call `attach_delivery(...)`
- fail closed without rewriting acceptance state

- [ ] **Step 4: Run tests to verify they pass**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/product/delivery/service.py tests/test_delivery_service.py
git commit -m "feat: add delivery service orchestration"
```

### Task 5: Add CLI `deliver`

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_delivery_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_deliver_command_runs_delivery_for_selected_issues(tmp_path):
    result = runner.invoke(app, [...])
    assert result.exit_code == 0
    assert "delivered=1" in result.stdout


def test_deliver_command_reports_failed_delivery(tmp_path):
    result = runner.invoke(app, [...])
    assert result.exit_code == 1
    assert "failed=1" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_cli.py -v`
Expected: FAIL because CLI command does not exist yet

- [ ] **Step 3: Write minimal implementation**

Add:
- `nightshift deliver --issues ... --config ...`
- operator-friendly summary output
- non-traceback failure handling

- [ ] **Step 4: Run tests to verify they pass**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_delivery_cli.py
git commit -m "feat: add delivery cli command"
```

### Task 6: Add `run --deliver` Convenience Hook

**Files:**
- Modify: `src/nightshift/cli/app.py`
- Test: `tests/test_execution_selection_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_run_with_deliver_invokes_delivery_for_accepted_issues(tmp_path):
    result = runner.invoke(app, [..., "--deliver"])
    assert result.exit_code == 0
    assert "issues_accepted" in result.stdout
    assert "delivered=1" in result.stdout


def test_run_with_deliver_skips_delivery_when_no_issue_is_accepted(tmp_path):
    result = runner.invoke(app, [..., "--deliver"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_execution_selection_cli.py -v`
Expected: FAIL because `--deliver` does not exist yet

- [ ] **Step 3: Write minimal implementation**

Hook delivery into `run` so that:
- accepted issue ids are collected from the batch result
- the same delivery service is called
- no second delivery path is invented

- [ ] **Step 4: Run tests to verify they pass**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_execution_selection_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nightshift/cli/app.py tests/test_execution_selection_cli.py
git commit -m "feat: add run deliver convenience hook"
```

### Task 7: Sync Docs And Rehearsal

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/product/README.md`
- Modify: `docs/mvp-walkthrough.md`
- Optional: `docs/2026-03-28-workflow-verification-report.md`

- [ ] **Step 1: Write/update docs**

Add:
- delivery command examples
- delivery prerequisites
- current live workflow now including PR creation

- [ ] **Step 2: Run focused command checks**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" python -m nightshift.cli.main deliver --help
PATH="$PWD/.venv/bin:$PATH" python -m nightshift.cli.main run --help
```

Expected:
- help output includes delivery commands/options

- [ ] **Step 3: Commit**

```bash
git add README.md docs/architecture/product/README.md docs/mvp-walkthrough.md docs/2026-03-28-workflow-verification-report.md
git commit -m "docs: add delivery workflow guidance"
```

### Task 8: Final Verification

**Files:**
- Verify whole repo; no planned file creation

- [ ] **Step 1: Run targeted suites**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_delivery_models.py tests/test_delivery_admission.py tests/test_delivery_rendering.py tests/test_delivery_service.py tests/test_delivery_cli.py -v
```

Expected:
- PASS

- [ ] **Step 2: Run full test suite**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest -q
```

Expected:
- PASS

- [ ] **Step 3: Run live workflow rehearsal**

Run the real product path:

```bash
PATH="$PWD/.venv/bin:$PATH" python -m nightshift.cli.main run --issues GH-7 --config /Users/gongmeng/dev/code/nightshift/nightshift.rehearsal.yaml --deliver
```

Or, if reusing an already accepted issue:

```bash
PATH="$PWD/.venv/bin:$PATH" python -m nightshift.cli.main deliver --issues GH-7 --config /Users/gongmeng/dev/code/nightshift/nightshift.rehearsal.yaml
```

Expected:
- PR is created
- `IssueRecord.delivery_state == submitted`
- `IssueRecord.delivery_ref` contains the PR URL

- [ ] **Step 4: Commit final fixes if needed**

```bash
git add <relevant files>
git commit -m "fix: close delivery workflow gaps"
```
