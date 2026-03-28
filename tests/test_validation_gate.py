from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nightshift.domain import AttemptState, IssueKind
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.records import AttemptRecord
from nightshift.validation.gate import ValidationResult, evaluate_acceptance, validate


def make_stage(command: str, *, required: bool) -> VerificationStageContract:
    return VerificationStageContract(
        required=required,
        commands=(command,),
        pass_condition=PassConditionContract(type="exit_code", expected=0),
    )


def make_contract(
    *,
    issue_validation: VerificationStageContract | None,
    regression_validation: VerificationStageContract | None,
    static_validation: VerificationStageContract | None = None,
) -> IssueContract:
    return IssueContract(
        issue_id="ISSUE-1",
        title="Validate the gate",
        kind=IssueKind.execution,
        priority="high",
        goal="Run validation checks",
        allowed_paths=("src",),
        forbidden_paths=("secrets",),
        verification=VerificationContract(
            issue_validation=issue_validation,
            regression_validation=regression_validation,
            static_validation=static_validation,
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


def make_attempt_record() -> AttemptRecord:
    return AttemptRecord(
        attempt_id="ATT-1",
        issue_id="ISSUE-1",
        run_id="RUN-1",
        engine_name="codex",
        engine_invocation_id="INV-1",
        attempt_state=AttemptState.validating,
        artifact_dir="artifacts/ATT-1",
        started_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
    )


def test_validation_gate_requires_issue_validation() -> None:
    contract = make_contract(
        issue_validation=None,
        regression_validation=make_stage("python3 -c \"print('regression')\"", required=True),
    )

    result = validate(contract, Path("."), make_attempt_record())

    assert result.passed is False
    assert result.failed_stage == "issue_validation"
    assert result.stages[0].stage_name == "issue_validation"
    assert result.stages[0].skipped is True
    assert result.stages[0].passed is False


def test_validation_gate_requires_regression_validation() -> None:
    contract = make_contract(
        issue_validation=make_stage("python3 -c \"print('issue')\"", required=True),
        regression_validation=None,
    )

    result = validate(contract, Path("."), make_attempt_record())

    assert result.passed is False
    assert result.failed_stage == "regression_validation"
    assert [stage.stage_name for stage in result.stages] == ["issue_validation", "regression_validation"]
    assert result.stages[0].passed is True
    assert result.stages[1].skipped is True
    assert result.stages[1].passed is False


def test_validation_gate_allows_optional_static_validation_to_fail_without_blocking() -> None:
    contract = make_contract(
        issue_validation=make_stage("python3 -c \"print('issue')\"", required=True),
        regression_validation=make_stage("python3 -c \"print('regression')\"", required=True),
        static_validation=VerificationStageContract(
            required=False,
            commands=("python3 -c \"import sys; sys.exit(1)\"",),
            pass_condition=PassConditionContract(type="exit_code", expected=0),
        ),
    )

    result = validate(contract, Path("."), make_attempt_record())

    assert result.passed is True
    assert result.failed_stage is None
    assert [stage.stage_name for stage in result.stages] == [
        "issue_validation",
        "regression_validation",
        "static_validation",
    ]
    assert result.stages[2].required is False
    assert result.stages[2].passed is False
    assert result.stages[2].skipped is False


def test_validation_gate_honors_pass_conditions() -> None:
    contract = make_contract(
        issue_validation=VerificationStageContract(
            required=True,
            commands=("python3 -c \"import sys; sys.exit(1)\"",),
            pass_condition=PassConditionContract(type="exit_code", expected=0),
        ),
        regression_validation=make_stage("python3 -c \"print('regression')\"", required=True),
    )

    result = validate(contract, Path("."), make_attempt_record())

    assert result.passed is False
    assert result.failed_stage == "issue_validation"
    assert result.stages[0].passed is False
    assert result.stages[0].command_results[0].exit_code == 1


def test_evaluate_acceptance_returns_passed_flag() -> None:
    passed = ValidationResult(
        passed=True,
        failed_stage=None,
        stages=(),
        summary="ok",
        raw_artifact_paths=(),
        evaluated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
    )
    failed = ValidationResult(
        passed=False,
        failed_stage="issue_validation",
        stages=(),
        summary="nope",
        raw_artifact_paths=(),
        evaluated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
    )

    assert evaluate_acceptance(passed) is True
    assert evaluate_acceptance(failed) is False
