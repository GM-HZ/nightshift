from __future__ import annotations

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
from nightshift.product.work_orders.models import WorkOrderEngineHints, WorkOrderFrontmatter
from nightshift.product.work_orders.parser import ParsedWorkOrder


def make_config() -> NightShiftConfig:
    return NightShiftConfig(
        project=ProjectConfig(repo_path=".", main_branch="main"),
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


def make_parsed_work_order(*, structured_verification: bool = False) -> ParsedWorkOrder:
    execution: dict[str, object] = {
        "title": "Add Chinese README",
        "goal": "Add a Chinese README and link it from the main README.",
        "allowed_paths": ["README.md", "README.zh-CN.md"],
        "non_goals": ["Change packaging", "Rewrite unrelated docs"],
        "acceptance_criteria": [
            "README.zh-CN.md exists and is non-empty",
            "README.md links to README.zh-CN.md",
        ],
        "context_files": ["README.md"],
    }
    if structured_verification:
        execution["verification"] = {
            "issue_validation": ["test -s README.zh-CN.md"],
            "regression_validation": ['rg -n "README\\.zh-CN\\.md" README.md'],
            "promotion_validation": [],
        }
    else:
        execution["verification_commands"] = [
            "test -s README.zh-CN.md",
            'rg -n "README\\.zh-CN\\.md" README.md',
        ]

    return ParsedWorkOrder(
        frontmatter=WorkOrderFrontmatter.model_validate(
            {
                "work_order_id": "WO-20260329-001",
                "status": "approved",
                "source_issue": {
                    "repo": "GM-HZ/nightshift",
                    "number": 7,
                    "url": "https://github.com/GM-HZ/nightshift/issues/7",
                },
                "execution": execution,
                "rationale": {
                    "summary": "Add a Chinese entry point without expanding scope into a full docs rewrite.",
                },
            }
        ),
        body="# Execution Work Order\n\nHuman-readable notes are not materialized.\n",
    )


def test_materialize_work_order_fills_defaults_and_normalizes_verification_commands() -> None:
    from nightshift.product.work_orders.materialize import (
        WorkOrderMaterializationProvenance,
        materialize_work_order,
    )

    parsed = make_parsed_work_order()

    contract = materialize_work_order(
        parsed,
        make_config(),
        WorkOrderMaterializationProvenance(
            work_order_path=".nightshift/work-orders/WO-20260329-001.md",
            work_order_revision="abc123def456",
            source_branch="feature/wo-20260329-001",
            source_pr="17",
        ),
    )

    assert contract.issue_id == "WO-20260329-001"
    assert contract.work_order_id == "WO-20260329-001"
    assert contract.priority == "high"
    assert contract.forbidden_paths == ("secrets", "dist")
    assert contract.acceptance == (
        "README.zh-CN.md exists and is non-empty",
        "README.md links to README.zh-CN.md",
    )
    assert contract.engine_preferences.primary == "codex"
    assert contract.engine_preferences.fallback == "claude"
    assert contract.verification.issue_validation is not None
    assert contract.verification.issue_validation.required is True
    assert contract.verification.issue_validation.commands == (
        "test -s README.zh-CN.md",
        'rg -n "README\\.zh-CN\\.md" README.md',
    )
    assert contract.verification.regression_validation is not None
    assert contract.verification.regression_validation.commands == (
        "test -s README.zh-CN.md",
        'rg -n "README\\.zh-CN\\.md" README.md',
    )
    assert contract.verification.promotion_validation is not None
    assert contract.verification.promotion_validation.required is False
    assert contract.verification.promotion_validation.commands == ()
    assert contract.work_order_path == ".nightshift/work-orders/WO-20260329-001.md"
    assert contract.work_order_revision == "abc123def456"
    assert contract.source_issue is not None
    assert contract.source_issue.repo == "GM-HZ/nightshift"
    assert contract.source_branch == "feature/wo-20260329-001"
    assert contract.source_pr == "17"


def test_materialize_work_order_preserves_structured_verification_and_explicit_issue_id() -> None:
    from nightshift.product.work_orders.materialize import (
        WorkOrderMaterializationProvenance,
        materialize_work_order,
    )

    parsed = make_parsed_work_order(structured_verification=True)
    parsed = ParsedWorkOrder(
        frontmatter=parsed.frontmatter.model_copy(
            update={
                "execution": parsed.frontmatter.execution.model_copy(
                    update={
                        "issue_id": "ISSUE-7",
                        "priority": "urgent",
                        "engine_hints": WorkOrderEngineHints(primary="claude", fallback="codex"),
                    }
                )
            }
        ),
        body=parsed.body,
    )

    contract = materialize_work_order(
        parsed,
        make_config(),
        WorkOrderMaterializationProvenance(
            work_order_path=".nightshift/work-orders/WO-20260329-001.md",
            work_order_revision="def456abc123",
        ),
    )

    assert contract.issue_id == "ISSUE-7"
    assert contract.work_order_id == "WO-20260329-001"
    assert contract.priority == "urgent"
    assert contract.engine_preferences.primary == "claude"
    assert contract.engine_preferences.fallback == "codex"
    assert contract.verification.issue_validation is not None
    assert contract.verification.issue_validation.commands == ("test -s README.zh-CN.md",)
    assert contract.verification.regression_validation is not None
    assert contract.verification.regression_validation.commands == ('rg -n "README\\.zh-CN\\.md" README.md',)
    assert contract.verification.promotion_validation is not None
    assert contract.verification.promotion_validation.commands == ()


def test_materialize_work_order_rejects_ambiguous_verification_inputs() -> None:
    from nightshift.product.work_orders.materialize import (
        WorkOrderMaterializationError,
        WorkOrderMaterializationProvenance,
        materialize_work_order,
    )

    parsed = make_parsed_work_order(structured_verification=True)
    parsed = ParsedWorkOrder(
        frontmatter=parsed.frontmatter.model_copy(
            update={
                "execution": parsed.frontmatter.execution.model_copy(
                    update={"verification_commands": ("test -s README.zh-CN.md",)}
                )
            }
        ),
        body=parsed.body,
    )

    with pytest.raises(WorkOrderMaterializationError, match="both verification"):
        materialize_work_order(
            parsed,
            make_config(),
            WorkOrderMaterializationProvenance(
                work_order_path=".nightshift/work-orders/WO-20260329-001.md",
                work_order_revision="abc123def456",
            ),
        )


def test_materialize_work_order_rejects_missing_required_execution_fields() -> None:
    from nightshift.product.work_orders.materialize import (
        WorkOrderMaterializationError,
        WorkOrderMaterializationProvenance,
        materialize_work_order,
    )

    parsed = make_parsed_work_order()
    parsed = ParsedWorkOrder(
        frontmatter=parsed.frontmatter.model_copy(
            update={
                "execution": parsed.frontmatter.execution.model_copy(
                    update={"goal": None}
                )
            }
        ),
        body=parsed.body,
    )

    with pytest.raises(WorkOrderMaterializationError, match="execution.goal"):
        materialize_work_order(
            parsed,
            make_config(),
            WorkOrderMaterializationProvenance(
                work_order_path=".nightshift/work-orders/WO-20260329-001.md",
                work_order_revision="abc123def456",
            ),
        )
