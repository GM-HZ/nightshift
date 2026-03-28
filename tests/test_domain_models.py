import pytest
from pydantic import ValidationError

from nightshift.domain.contracts import (
    AttemptLimitsContract,
    EnginePreferencesContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.records import IssueRecord
from nightshift.domain.records import AttemptRecord


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
                "pass_condition": {
                    "type": "exit_code",
                    "expected": 0,
                },
            }
        },
        "engine_preferences": {
            "primary": "gpt-5",
            "fallback": "gpt-4.1",
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
                commands=("pytest",),
                pass_condition=PassConditionContract(type="exit_code", expected=0),
            )
        ),
        engine_preferences=EnginePreferencesContract(primary="gpt-5", fallback="gpt-4.1"),
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

    with pytest.raises(AttributeError):
        contract.allowed_paths.append("more")

    with pytest.raises(AttributeError):
        contract.verification.issue_validation.commands.append("more")

    assert contract.engine_preferences.primary == "gpt-5"
    assert contract.engine_preferences.fallback == "gpt-4.1"


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
        engine_preferences=EnginePreferencesContract(primary="gpt-5", fallback="gpt-4.1"),
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


def test_execution_contract_requires_paths_and_validation() -> None:
    contract = IssueContract(
        issue_id="ISSUE-1",
        title="Run execution work",
        kind="execution",
        priority="high",
        goal="Do the execution task",
        allowed_paths=["src"],
        forbidden_paths=["secrets"],
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=("pytest",),
                pass_condition=PassConditionContract(type="exit_code", expected=0),
            )
        ),
        engine_preferences=EnginePreferencesContract(primary="gpt-5", fallback=None),
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(),
    )

    assert contract.kind == "execution"


def test_execution_contract_rejects_commands_without_pass_condition() -> None:
    with pytest.raises(ValidationError):
        IssueContract(
            issue_id="ISSUE-1",
            title="Run execution work",
            kind="execution",
            priority="high",
            goal="Do the execution task",
            allowed_paths=["src"],
            forbidden_paths=["secrets"],
            verification=VerificationContract(
                issue_validation=VerificationStageContract(
                    required=True,
                    commands=("pytest",),
                    pass_condition=None,
                )
            ),
            engine_preferences=EnginePreferencesContract(primary="gpt-5", fallback=None),
            test_edit_policy=TestEditPolicyContract(
                can_add_tests=True,
                can_modify_existing_tests=True,
                can_weaken_assertions=False,
                requires_test_change_reason=True,
            ),
            attempt_limits=AttemptLimitsContract(),
            timeouts=TimeoutsContract(),
        )


def test_execution_contract_rejects_unknown_pass_condition_type() -> None:
    with pytest.raises(ValidationError):
        IssueContract(
            issue_id="ISSUE-1",
            title="Run execution work",
            kind="execution",
            priority="high",
            goal="Do the execution task",
            allowed_paths=["src"],
            forbidden_paths=["secrets"],
            verification=VerificationContract(
                issue_validation=VerificationStageContract(
                    required=True,
                    commands=("pytest",),
                    pass_condition={"type": "bogus"},
                )
            ),
            engine_preferences=EnginePreferencesContract(primary="gpt-5", fallback=None),
            test_edit_policy=TestEditPolicyContract(
                can_add_tests=True,
                can_modify_existing_tests=True,
                can_weaken_assertions=False,
                requires_test_change_reason=True,
            ),
            attempt_limits=AttemptLimitsContract(),
            timeouts=TimeoutsContract(),
        )


def test_execution_contract_rejects_empty_allowed_paths() -> None:
    with pytest.raises(ValidationError):
        IssueContract(
            issue_id="ISSUE-1",
            title="Run execution work",
            kind="execution",
            priority="high",
            goal="Do the execution task",
            allowed_paths=[],
            forbidden_paths=["secrets"],
            verification=VerificationContract(
                issue_validation=VerificationStageContract(
                    required=True,
                    commands=("pytest",),
                    pass_condition=PassConditionContract(type="exit_code", expected=0),
                )
            ),
            engine_preferences=EnginePreferencesContract(primary="gpt-5", fallback=None),
            test_edit_policy=TestEditPolicyContract(
                can_add_tests=True,
                can_modify_existing_tests=True,
                can_weaken_assertions=False,
                requires_test_change_reason=True,
            ),
            attempt_limits=AttemptLimitsContract(),
            timeouts=TimeoutsContract(),
        )


def test_execution_contract_rejects_empty_verification() -> None:
    with pytest.raises(ValidationError):
        IssueContract(
            issue_id="ISSUE-1",
            title="Run execution work",
            kind="execution",
            priority="high",
            goal="Do the execution task",
            allowed_paths=["src"],
            forbidden_paths=["secrets"],
            verification=VerificationContract(),
            engine_preferences=EnginePreferencesContract(primary="gpt-5", fallback=None),
            test_edit_policy=TestEditPolicyContract(
                can_add_tests=True,
                can_modify_existing_tests=True,
                can_weaken_assertions=False,
                requires_test_change_reason=True,
            ),
            attempt_limits=AttemptLimitsContract(),
            timeouts=TimeoutsContract(),
        )


def test_attempt_record_requires_validation_pass_for_accepted() -> None:
    with pytest.raises(ValidationError) as exc_info:
        AttemptRecord.model_validate(
            {
                "attempt_id": "ATT-1",
                "issue_id": "ISSUE-1",
                "run_id": "RUN-1",
                "engine_name": "gpt-5",
                "engine_invocation_id": "INV-1",
                "attempt_state": "accepted",
                "validation_result": {"passed": False},
            }
        )

    assert "accepted attempts require a passing validation_result" in str(exc_info.value)


def test_attempt_record_requires_preflight_failed_to_be_false() -> None:
    with pytest.raises(ValidationError) as exc_info:
        AttemptRecord.model_validate(
            {
                "attempt_id": "ATT-1",
                "issue_id": "ISSUE-1",
                "run_id": "RUN-1",
                "engine_name": "gpt-5",
                "engine_invocation_id": "INV-1",
                "attempt_state": "preflight_failed",
                "preflight_passed": True,
            }
        )

    assert "preflight_failed attempts require preflight_passed to be False" in str(exc_info.value)


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
