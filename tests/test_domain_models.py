import pytest
from pydantic import ValidationError

from nightshift.domain.contracts import (
    AttemptLimitsContract,
    IssueContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.records import IssueRecord


def test_issue_contract_rejects_runtime_fields() -> None:
    payload = {
        "issue_id": "ISSUE-1",
        "title": "Implement feature",
        "kind": "task",
        "priority": "high",
        "goal": "Ship the feature",
        "allowed_paths": ["src"],
        "forbidden_paths": ["secrets"],
        "verification": {
            "issue_validation": {
                "required": True,
                "commands": ["pytest"],
                "pass_condition": "exit_code_zero",
            }
        },
        "engine_preferences": {
            "primary": ["gpt-5"],
            "fallback": ["gpt-4.1"],
        },
        "test_edit_policy": {
            "can_add_tests": True,
            "can_modify_existing_tests": True,
            "can_weaken_assertions": False,
            "requires_test_change_reason": True,
        },
        "attempt_limits": {
            "max_files_changed": 3,
            "max_lines_added": 200,
            "max_lines_deleted": 50,
        },
        "timeouts": {
            "command_seconds": 900,
            "issue_budget_seconds": 7200,
        },
        "issue_state": "ready",
    }

    with pytest.raises(ValidationError):
        IssueContract.model_validate(payload)


def test_issue_contract_is_frozen_after_creation() -> None:
    contract = IssueContract(
        issue_id="ISSUE-1",
        title="Implement feature",
        kind="task",
        priority="high",
        goal="Ship the feature",
        allowed_paths=["src"],
        forbidden_paths=["secrets"],
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=["pytest"],
                pass_condition="exit_code_zero",
            )
        ),
        engine_preferences={"primary": ["gpt-5"], "fallback": ["gpt-4.1"]},
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(
            max_files_changed=3,
            max_lines_added=200,
            max_lines_deleted=50,
        ),
        timeouts=TimeoutsContract(command_seconds=900, issue_budget_seconds=7200),
    )

    with pytest.raises(ValidationError):
        contract.priority = "low"

    assert contract.engine_preferences.primary == ["gpt-5"]
    assert contract.engine_preferences.fallback == ["gpt-4.1"]


def test_issue_record_from_contract_seeds_queue_priority() -> None:
    contract = IssueContract(
        issue_id="ISSUE-1",
        title="Implement feature",
        kind="task",
        priority="high",
        goal="Ship the feature",
        allowed_paths=["src"],
        forbidden_paths=["secrets"],
        verification=VerificationContract(),
        engine_preferences={"primary": ["gpt-5"], "fallback": ["gpt-4.1"]},
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(),
    )

    record = IssueRecord.from_contract(
        contract,
        issue_state="draft",
        attempt_state="pending",
        delivery_state="none",
        created_at="2026-03-28T00:00:00Z",
        updated_at="2026-03-28T00:00:00Z",
    )

    assert record.queue_priority == contract.priority


def test_issue_record_exposes_delivery_fields() -> None:
    record = IssueRecord.model_validate(
        {
            "issue_id": "ISSUE-1",
            "issue_state": "draft",
            "attempt_state": "pending",
            "delivery_state": "none",
            "queue_priority": "high",
            "created_at": "2026-03-28T00:00:00Z",
            "updated_at": "2026-03-28T00:00:00Z",
        }
    )

    assert hasattr(record, "queue_priority")
    assert hasattr(record, "delivery_id")
    assert hasattr(record, "delivery_ref")
