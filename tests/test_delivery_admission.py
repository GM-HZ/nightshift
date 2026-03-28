from __future__ import annotations

from pathlib import Path

from nightshift.domain import AttemptState, DeliveryState, IssueKind, IssueState
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.records import IssueRecord
from nightshift.product.delivery.admission import evaluate_deliverability


def make_contract(issue_id: str) -> IssueContract:
    return IssueContract(
        issue_id=issue_id,
        title=f"Title for {issue_id}",
        kind=IssueKind.execution,
        priority="high",
        goal="Ship the thing",
        allowed_paths=("README.md",),
        forbidden_paths=("secrets",),
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=("pytest",),
                pass_condition=PassConditionContract(type="exit_code", expected=0),
            ),
            regression_validation=VerificationStageContract(
                required=True,
                commands=("pytest",),
                pass_condition=PassConditionContract(type="exit_code", expected=0),
            ),
        ),
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(),
    )


def make_record(issue_id: str, worktree_path: Path, **extra: object) -> IssueRecord:
    payload = {
        "issue_id": issue_id,
        "issue_state": IssueState.done,
        "attempt_state": AttemptState.accepted,
        "delivery_state": DeliveryState.none,
        "accepted_attempt_id": "ATT-1",
        "branch_name": f"nightshift-issue-{issue_id.lower()}",
        "worktree_path": str(worktree_path),
        "queue_priority": "high",
        "created_at": "2026-03-29T00:00:00Z",
        "updated_at": "2026-03-29T00:00:00Z",
        **extra,
    }
    return IssueRecord.model_validate(payload)


def test_evaluate_deliverability_accepts_done_and_accepted_issue(tmp_path: Path) -> None:
    worktree = tmp_path / ".worktrees" / "issue-GH-7"
    worktree.mkdir(parents=True)

    result = evaluate_deliverability(make_contract("GH-7"), make_record("GH-7", worktree))

    assert result.allowed is True
    assert result.reason is None


def test_evaluate_deliverability_rejects_non_accepted_issue(tmp_path: Path) -> None:
    worktree = tmp_path / ".worktrees" / "issue-GH-7"
    worktree.mkdir(parents=True)
    record = make_record("GH-7", worktree, issue_state=IssueState.ready, attempt_state=AttemptState.pending)

    result = evaluate_deliverability(make_contract("GH-7"), record)

    assert result.allowed is False
    assert "accepted" in result.reason


def test_evaluate_deliverability_rejects_existing_delivery_ref(tmp_path: Path) -> None:
    worktree = tmp_path / ".worktrees" / "issue-GH-7"
    worktree.mkdir(parents=True)
    record = make_record(
        "GH-7",
        worktree,
        delivery_state=DeliveryState.pr_opened,
        delivery_ref="https://github.com/GM-HZ/nightshift/pull/7",
        delivery_id="7",
    )

    result = evaluate_deliverability(make_contract("GH-7"), record)

    assert result.allowed is False
    assert "already has delivery" in result.reason


def test_evaluate_deliverability_rejects_missing_worktree(tmp_path: Path) -> None:
    missing = tmp_path / ".worktrees" / "issue-GH-7"

    result = evaluate_deliverability(make_contract("GH-7"), make_record("GH-7", missing))

    assert result.allowed is False
    assert "worktree" in result.reason
