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
from nightshift.domain.records import IssueRecord
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


def make_record(
    issue_id: str,
    *,
    issue_state: IssueState = IssueState.draft,
    attempt_state: AttemptState = AttemptState.pending,
    queue_priority: str = "medium",
    **extra: object,
) -> IssueRecord:
    return IssueRecord.model_validate(
        {
            "issue_id": issue_id,
            "issue_state": issue_state,
            "attempt_state": attempt_state,
            "delivery_state": DeliveryState.none,
            "queue_priority": queue_priority,
            "created_at": "2026-03-29T00:00:00Z",
            "updated_at": "2026-03-29T00:00:00Z",
            **extra,
        }
    )


def write_work_order(
    repo_root: Path,
    *,
    work_order_id: str = "WO-20260329-001",
    title: str = "Add Chinese README",
    goal: str = "Add a Chinese README and link it from the main README.",
    issue_id: str | None = None,
    include_goal: bool = True,
) -> Path:
    issue_id_block = f"  issue_id: {issue_id}\n" if issue_id is not None else ""
    goal_block = f"  goal: {goal}\n" if include_goal else ""
    markdown = f"""---
work_order_id: {work_order_id}
status: approved
source_issue:
  repo: GM-HZ/nightshift
  number: 7
  url: https://github.com/GM-HZ/nightshift/issues/7
execution:
  title: {title}
{goal_block}  allowed_paths:
    - README.md
    - README.zh-CN.md
  non_goals:
    - Change packaging
  acceptance_criteria:
    - README.zh-CN.md exists and is non-empty
    - README.md links to README.zh-CN.md
  context_files:
    - README.md
{issue_id_block}  verification_commands:
    - test -s README.zh-CN.md
    - rg -n "README\\\\.zh-CN\\\\.md" README.md
rationale:
  summary: Add a Chinese entry point without expanding scope.
---
# Execution Work Order

Human-readable notes are not materialized.
"""
    path = repo_root / ".nightshift" / "work-orders" / f"{work_order_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown)
    return path


def test_admit_to_queue_freezes_current_work_order_and_persists_revisioned_contract(tmp_path: Path) -> None:
    from nightshift.product.queue_admission import admit_to_queue

    repo_root = tmp_path
    config = make_config(repo_root)
    registry = IssueRegistry(repo_root)
    write_work_order(repo_root)
    registry.save_record(make_record("WO-20260329-001"))

    result = admit_to_queue(registry, ["WO-20260329-001"], config=config)

    assert result.summary.requested == 1
    assert result.summary.admitted == 1
    assert result.statuses[0].issue_id == "WO-20260329-001"
    assert result.statuses[0].status == "admitted"
    contract = registry.get_contract("WO-20260329-001")
    record = registry.get_record("WO-20260329-001")
    assert contract.work_order_id == "WO-20260329-001"
    assert contract.work_order_path == ".nightshift/work-orders/WO-20260329-001.md"
    assert contract.work_order_revision is not None
    assert contract.non_goals == ("Change packaging",)
    assert contract.context_files == ("README.md",)
    assert record.issue_state == IssueState.ready
    assert record.queue_priority == "medium"
    revisions = registry.list_contract_revisions("WO-20260329-001")
    assert [revision.work_order_revision for revision in revisions] == [contract.work_order_revision]


def test_admit_to_queue_fails_cleanly_when_work_order_materialization_fails(tmp_path: Path) -> None:
    from nightshift.product.queue_admission import admit_to_queue

    repo_root = tmp_path
    config = make_config(repo_root)
    registry = IssueRegistry(repo_root)
    write_work_order(repo_root, include_goal=False)
    original_record = make_record("WO-20260329-001")
    registry.save_record(original_record)

    with pytest.raises(ValueError, match="materializ|execution.goal"):
        admit_to_queue(registry, ["WO-20260329-001"], config=config)

    assert registry.get_record("WO-20260329-001") == original_record
    with pytest.raises(FileNotFoundError):
        registry.get_contract("WO-20260329-001")
    assert registry.list_contract_revisions("WO-20260329-001") == []


def test_admit_to_queue_rematerializes_after_work_order_drift_and_preserves_history(tmp_path: Path) -> None:
    from nightshift.product.queue_admission import admit_to_queue

    repo_root = tmp_path
    config = make_config(repo_root)
    registry = IssueRegistry(repo_root)
    write_work_order(repo_root, title="Add Chinese README")
    registry.save_record(make_record("WO-20260329-001"))

    first = admit_to_queue(registry, ["WO-20260329-001"], config=config)
    first_contract = registry.get_contract("WO-20260329-001")

    write_work_order(repo_root, title="Add localized Chinese README")
    second = admit_to_queue(registry, ["WO-20260329-001"], config=config)
    latest_contract = registry.get_contract("WO-20260329-001")

    assert first.summary.admitted == 1
    assert second.summary.admitted == 1
    assert first_contract.title == "Add Chinese README"
    assert latest_contract.title == "Add localized Chinese README"
    assert latest_contract.work_order_revision != first_contract.work_order_revision
    revisions = registry.list_contract_revisions("WO-20260329-001")
    assert [revision.title for revision in revisions] == [
        "Add Chinese README",
        "Add localized Chinese README",
    ]
    assert revisions[0].work_order_revision == first_contract.work_order_revision
    assert revisions[1].work_order_revision == latest_contract.work_order_revision
