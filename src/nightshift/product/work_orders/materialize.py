from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nightshift.config.models import NightShiftConfig
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    EnginePreferencesContract,
    IssueContract,
    PassConditionContract,
    SourceIssueContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.enums import IssueKind
from nightshift.product.work_orders.models import WorkOrderExecution, WorkOrderFrontmatter
from nightshift.product.work_orders.parser import ParsedWorkOrder


class WorkOrderMaterializationError(ValueError):
    """Raised when a parsed work order cannot be materialized into a runtime contract."""


@dataclass(frozen=True, slots=True)
class WorkOrderMaterializationProvenance:
    work_order_path: str
    work_order_revision: str
    source_branch: str | None = None
    source_pr: str | None = None


def materialize_work_order(
    work_order: ParsedWorkOrder | WorkOrderFrontmatter,
    config: NightShiftConfig,
    provenance: WorkOrderMaterializationProvenance,
) -> IssueContract:
    frontmatter = work_order.frontmatter if isinstance(work_order, ParsedWorkOrder) else work_order
    execution = frontmatter.execution

    _validate_required_execution_fields(execution)

    if execution.verification is not None and execution.verification_commands:
        raise WorkOrderMaterializationError(
            "execution cannot declare both verification and verification_commands"
        )

    verification = _materialize_verification(execution)
    issue_defaults = config.issue_defaults

    return IssueContract(
        issue_id=execution.issue_id or frontmatter.work_order_id,
        title=execution.title,
        kind=IssueKind.execution,
        goal=execution.goal,
        allowed_paths=tuple(execution.allowed_paths),
        forbidden_paths=tuple(execution.forbidden_paths or issue_defaults.default_forbidden_paths),
        non_goals=tuple(execution.non_goals),
        context_files=tuple(execution.context_files),
        verification=verification,
        test_edit_policy=_materialize_test_edit_policy(execution, config),
        attempt_limits=_materialize_attempt_limits(execution, config),
        timeouts=_materialize_timeouts(execution, config),
        priority=execution.priority or issue_defaults.default_priority,
        engine_preferences=_materialize_engine_preferences(execution, config),
        acceptance=tuple(execution.acceptance_criteria),
        work_order_id=frontmatter.work_order_id,
        work_order_path=provenance.work_order_path,
        work_order_revision=provenance.work_order_revision,
        source_issue=SourceIssueContract(
            repo=frontmatter.source_issue.repo,
            number=frontmatter.source_issue.number,
            url=frontmatter.source_issue.url,
        ),
        source_branch=provenance.source_branch,
        source_pr=provenance.source_pr,
    )


def _validate_required_execution_fields(execution: WorkOrderExecution) -> None:
    _require_non_empty_value("execution.title", execution.title)
    _require_non_empty_value("execution.goal", execution.goal)
    _require_non_empty_sequence("execution.allowed_paths", execution.allowed_paths)
    _require_non_empty_sequence("execution.non_goals", execution.non_goals)
    _require_non_empty_sequence("execution.acceptance_criteria", execution.acceptance_criteria)
    _require_non_empty_sequence("execution.context_files", execution.context_files)

    if execution.verification is not None and execution.verification_commands:
        raise WorkOrderMaterializationError(
            "execution cannot declare both verification and verification_commands"
        )

    if execution.verification is None and not execution.verification_commands:
        raise WorkOrderMaterializationError("execution requires verification or verification_commands")


def _require_non_empty_value(field_name: str, value: object) -> None:
    if value is None:
        raise WorkOrderMaterializationError(f"{field_name} is required")

    if isinstance(value, str) and not value.strip():
        raise WorkOrderMaterializationError(f"{field_name} must not be blank")


def _require_non_empty_sequence(field_name: str, value: Iterable[object] | None) -> None:
    if value is None:
        raise WorkOrderMaterializationError(f"{field_name} is required")

    items = tuple(value)
    if not items:
        raise WorkOrderMaterializationError(f"{field_name} must not be empty")

    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise WorkOrderMaterializationError(f"{field_name} must contain only non-empty strings")


def _materialize_verification(execution: WorkOrderExecution) -> VerificationContract:
    if execution.verification is not None:
        verification = execution.verification
        if not verification.has_commands():
            raise WorkOrderMaterializationError("execution.verification must declare at least one command")

        return VerificationContract(
            issue_validation=_stage_from_commands(verification.issue_validation),
            regression_validation=_stage_from_commands(verification.regression_validation),
            promotion_validation=_stage_from_commands(verification.promotion_validation),
        )

    commands = tuple(execution.verification_commands or ())
    if not commands:
        raise WorkOrderMaterializationError("execution.verification_commands must not be empty")

    stage = _stage_from_commands(commands)
    return VerificationContract(
        issue_validation=stage,
        regression_validation=stage,
        promotion_validation=_stage_from_commands(()),
    )


def _stage_from_commands(commands: Iterable[str]) -> VerificationStageContract:
    normalized_commands = tuple(commands)
    if normalized_commands:
        return VerificationStageContract(
            required=True,
            commands=normalized_commands,
            pass_condition=PassConditionContract(type="all_exit_codes_zero"),
        )

    return VerificationStageContract(required=False)


def _materialize_test_edit_policy(
    execution: WorkOrderExecution,
    config: NightShiftConfig,
) -> TestEditPolicyContract:
    source = execution.test_edit_policy or config.issue_defaults.default_test_edit_policy
    return TestEditPolicyContract(
        can_add_tests=source.can_add_tests,
        can_modify_existing_tests=source.can_modify_existing_tests,
        can_weaken_assertions=source.can_weaken_assertions,
        requires_test_change_reason=source.requires_test_change_reason,
    )


def _materialize_attempt_limits(
    execution: WorkOrderExecution,
    config: NightShiftConfig,
) -> AttemptLimitsContract:
    source = execution.attempt_limits or config.issue_defaults.default_attempt_limits
    return AttemptLimitsContract(
        max_files_changed=source.max_files_changed,
        max_lines_added=source.max_lines_added,
        max_lines_deleted=source.max_lines_deleted,
    )


def _materialize_timeouts(
    execution: WorkOrderExecution,
    config: NightShiftConfig,
) -> TimeoutsContract:
    source = execution.timeouts or config.issue_defaults.default_timeouts
    return TimeoutsContract(
        command_seconds=source.command_seconds,
        issue_budget_seconds=source.issue_budget_seconds,
    )


def _materialize_engine_preferences(
    execution: WorkOrderExecution,
    config: NightShiftConfig,
) -> EnginePreferencesContract:
    if execution.engine_hints is not None:
        return EnginePreferencesContract(
            primary=execution.engine_hints.primary,
            fallback=execution.engine_hints.fallback,
        )

    return EnginePreferencesContract(
        primary=config.runner.default_engine,
        fallback=config.runner.fallback_engine,
    )
