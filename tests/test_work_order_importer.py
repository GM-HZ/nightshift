from __future__ import annotations

from pathlib import Path

import pytest

from nightshift.config.models import (
    AlertsConfig,
    AttemptLimitsConfig,
    IssueDefaultsConfig,
    NightShiftConfig,
    ProjectConfig,
    ReportConfig,
    RetryConfig,
    RunnerConfig,
    SeverityThresholdsConfig,
    TestEditPolicyConfig,
    TimeoutsConfig,
    ValidationConfig,
    WorkspaceConfig,
)
from nightshift.domain import AttemptState, DeliveryState, IssueState
from nightshift.product.work_orders.importer import WorkOrderImportError, import_work_order
from nightshift.registry.issue_registry import IssueRegistry


def make_config(repo_root: Path) -> NightShiftConfig:
    return NightShiftConfig(
        project=ProjectConfig(repo_path=str(repo_root), main_branch="main"),
        runner=RunnerConfig(
            default_engine="codex",
            fallback_engine="claude",
            issue_timeout_seconds=7200,
            overnight_timeout_seconds=28800,
        ),
        validation=ValidationConfig(enabled=True),
        issue_defaults=IssueDefaultsConfig(
            default_priority="high",
            default_forbidden_paths=["secrets", "dist"],
            default_test_edit_policy=TestEditPolicyConfig(
                can_add_tests=True,
                can_modify_existing_tests=False,
                can_weaken_assertions=False,
                requires_test_change_reason=True,
            ),
            default_attempt_limits=AttemptLimitsConfig(
                max_files_changed=5,
                max_lines_added=500,
                max_lines_deleted=200,
            ),
            default_timeouts=TimeoutsConfig(
                command_seconds=900,
                issue_budget_seconds=7200,
            ),
        ),
        retry=RetryConfig(max_retries=1, retry_policy="never", failure_circuit_breaker=False),
        workspace=WorkspaceConfig(
            worktree_root=".nightshift/worktrees",
            artifact_root="nightshift-data/runs",
        ),
        alerts=AlertsConfig(
            enabled_channels=[],
            severity_thresholds=SeverityThresholdsConfig(
                info="info",
                warning="warning",
                critical="critical",
            ),
        ),
        report=ReportConfig(output_directory="nightshift-data/reports", summary_verbosity="concise"),
    )


def write_work_order(repo_root: Path, *, status: str = "approved") -> Path:
    markdown = f"""---
work_order_id: WO-20260409-001
status: {status}
source_issue:
  repo: GM-HZ/nightshift
  number: 9
  url: https://github.com/GM-HZ/nightshift/issues/9
execution:
  title: Add issue import command
  goal: Import approved work orders to issue storage.
  allowed_paths:
    - src/nightshift/cli/app.py
  non_goals:
    - Rewrite orchestrator
  acceptance_criteria:
    - issue import command exists
  context_files:
    - README.zh-CN.md
  verification_commands:
    - rg -n "issue import" src/nightshift/cli/app.py
rationale:
  summary: Remove manual issue-record bootstrap requirement.
---
# Execution Work Order
"""
    path = repo_root / ".nightshift" / "work-orders" / "WO-20260409-001.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown)
    return path


def test_import_work_order_creates_contract_and_record(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    work_order_path = write_work_order(tmp_path)

    result = import_work_order(
        registry,
        config=make_config(tmp_path),
        work_order_path=work_order_path,
        repo_root=tmp_path,
    )

    assert result.issue_id == "WO-20260409-001"
    assert result.record_created is True
    contract = registry.get_contract("WO-20260409-001")
    record = registry.get_record("WO-20260409-001")
    assert contract.work_order_path == ".nightshift/work-orders/WO-20260409-001.md"
    assert contract.work_order_revision is not None
    assert record.issue_state == IssueState.draft
    assert record.attempt_state == AttemptState.pending
    assert record.delivery_state == DeliveryState.none


def test_import_work_order_reuses_existing_record(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    work_order_path = write_work_order(tmp_path)
    config = make_config(tmp_path)

    first = import_work_order(registry, config=config, work_order_path=work_order_path, repo_root=tmp_path)
    second = import_work_order(registry, config=config, work_order_path=work_order_path, repo_root=tmp_path)

    assert first.record_created is True
    assert second.record_created is False


def test_import_work_order_rejects_non_approved_status(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    work_order_path = write_work_order(tmp_path, status="draft")

    with pytest.raises(WorkOrderImportError, match="approved"):
        import_work_order(
            registry,
            config=make_config(tmp_path),
            work_order_path=work_order_path,
            repo_root=tmp_path,
        )
