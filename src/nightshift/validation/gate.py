from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import shlex
import subprocess

from nightshift.domain.contracts import IssueContract, PassConditionContract, VerificationStageContract
from nightshift.domain.records import AttemptRecord


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    exit_code: int
    passed: bool
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class ValidationStageResult:
    stage_name: str
    required: bool
    passed: bool
    skipped: bool
    pass_condition: PassConditionContract | None
    command_results: tuple[CommandResult, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationResult:
    passed: bool
    failed_stage: str | None
    stages: tuple[ValidationStageResult, ...]
    summary: str
    raw_artifact_paths: tuple[str, ...] = ()
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def validate(issue_contract: IssueContract, workspace: object, attempt_record: AttemptRecord) -> ValidationResult:
    del attempt_record

    workspace_path = _workspace_path(workspace)
    stages: list[ValidationStageResult] = []

    issue_stage = _run_stage("issue_validation", issue_contract.verification.issue_validation, workspace_path)
    stages.append(issue_stage)
    if issue_stage.required and not issue_stage.passed:
        return _failure_result("issue_validation", stages)

    regression_stage = _run_stage("regression_validation", issue_contract.verification.regression_validation, workspace_path)
    stages.append(regression_stage)
    if regression_stage.required and not regression_stage.passed:
        return _failure_result("regression_validation", stages)

    static_stage = _run_stage("static_validation", issue_contract.verification.static_validation, workspace_path)
    stages.append(static_stage)

    summary = "validation passed"
    if any(not stage.passed and not stage.required for stage in stages):
        summary = "validation passed with optional stage failures"

    return ValidationResult(
        passed=True,
        failed_stage=None,
        stages=tuple(stages),
        summary=summary,
    )


def evaluate_acceptance(validation_result: ValidationResult) -> bool:
    return validation_result.passed


def _run_stage(
    stage_name: str,
    stage: VerificationStageContract | None,
    workspace_path: Path,
) -> ValidationStageResult:
    if stage is None:
        required = stage_name in {"issue_validation", "regression_validation"}
        return ValidationStageResult(
            stage_name=stage_name,
            required=required,
            passed=not required,
            skipped=True,
            pass_condition=None,
            command_results=(),
        )

    if not stage.commands:
        return ValidationStageResult(
            stage_name=stage_name,
            required=stage.required,
            passed=True,
            skipped=True,
            pass_condition=stage.pass_condition,
            command_results=(),
        )

    command_results: list[CommandResult] = []
    for command in stage.commands:
        completed = subprocess.run(
            shlex.split(command),
            cwd=workspace_path,
            check=False,
            capture_output=True,
            text=True,
        )
        passed = _command_passed(completed.returncode, stage.pass_condition)
        command_results.append(
            CommandResult(
                command=command,
                exit_code=completed.returncode,
                passed=passed,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )

    stage_passed = all(command_result.passed for command_result in command_results)
    return ValidationStageResult(
        stage_name=stage_name,
        required=stage.required,
        passed=stage_passed,
        skipped=False,
        pass_condition=stage.pass_condition,
        command_results=tuple(command_results),
    )


def _command_passed(exit_code: int, pass_condition: PassConditionContract | None) -> bool:
    if pass_condition is None:
        return exit_code == 0

    if pass_condition.type == "exit_code":
        return exit_code == pass_condition.expected

    if pass_condition.type == "all_exit_codes_zero":
        return exit_code == 0

    return False


def _failure_result(failed_stage: str, stages: list[ValidationStageResult]) -> ValidationResult:
    return ValidationResult(
        passed=False,
        failed_stage=failed_stage,
        stages=tuple(stages),
        summary=f"{failed_stage} failed",
    )


def _workspace_path(workspace: object) -> Path:
    if isinstance(workspace, Path):
        return workspace

    if isinstance(workspace, str):
        return Path(workspace)

    candidate = getattr(workspace, "worktree_path", None)
    if candidate is not None:
        return Path(candidate)

    candidate = getattr(workspace, "path", None)
    if candidate is not None:
        return Path(candidate)

    raise TypeError("workspace must be a path or expose worktree_path")
