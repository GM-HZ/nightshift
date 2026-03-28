from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints, model_validator

from .enums import AlertSeverity, AttemptState, DeliveryState, IssueState, RunState as RunStateEnum

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AttemptValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    summary: str | None = None
    details: NonEmptyStr | dict[str, Any] | None = None
    exit_code: NonNegativeInt | None = None
    command: NonEmptyStr | None = None
    notes: NonEmptyStr | None = None


class IssueRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: NonEmptyStr
    issue_state: IssueState
    attempt_state: AttemptState
    delivery_state: DeliveryState
    queue_priority: NonEmptyStr
    delivery_id: NonEmptyStr | None = None
    delivery_ref: NonEmptyStr | None = None
    blocker_type: NonEmptyStr | None = None
    progress_type: NonEmptyStr | None = None
    current_run_id: NonEmptyStr | None = None
    latest_attempt_id: NonEmptyStr | None = None
    accepted_attempt_id: NonEmptyStr | None = None
    branch_name: NonEmptyStr | None = None
    worktree_path: NonEmptyStr | None = None
    retry_count: NonNegativeInt = 0
    deferred_reason: NonEmptyStr | None = None
    last_summary: NonEmptyStr | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_contract(cls, contract: "IssueContract", **data: Any) -> "IssueRecord":
        from .contracts import IssueContract

        if not isinstance(contract, IssueContract):
            raise TypeError("contract must be an IssueContract")

        overridden_fields = [field for field in ("issue_id", "queue_priority") if field in data]
        if overridden_fields:
            fields = ", ".join(overridden_fields)
            raise ValueError(f"contract-derived fields cannot be overridden: {fields}")

        payload = {"issue_id": contract.issue_id, "queue_priority": contract.priority, **data}
        return cls.model_validate(payload)

    @model_validator(mode="after")
    def validate_delivery_constraints(self) -> "IssueRecord":
        if self.issue_state == IssueState.blocked and not self.blocker_type:
            raise ValueError("blocker_type must be set when issue_state is blocked")

        if self.issue_state == IssueState.done and self.attempt_state != AttemptState.accepted:
            raise ValueError("done issues require attempt_state to be accepted")

        if self.issue_state == IssueState.done and not self.accepted_attempt_id:
            raise ValueError("done issues require accepted_attempt_id")

        if self.attempt_state == AttemptState.accepted and self.issue_state != IssueState.done:
            raise ValueError("accepted attempts require issue_state to be done")

        if self.delivery_state != DeliveryState.none and not self.accepted_attempt_id:
            raise ValueError("accepted_attempt_id must be set when delivery_state is not none")

        if self.delivery_state != DeliveryState.none and self.issue_state != IssueState.done:
            raise ValueError("delivery states require issue_state to be done")

        if self.delivery_state != DeliveryState.none and self.attempt_state != AttemptState.accepted:
            raise ValueError("delivery states require attempt_state to be accepted")

        if self.delivery_state == DeliveryState.branch_ready and not self.branch_name:
            raise ValueError("branch_ready delivery states require branch_name")

        if self.delivery_state in {
            DeliveryState.pr_opened,
            DeliveryState.reviewed,
            DeliveryState.merged,
            DeliveryState.closed_without_merge,
        } and not (self.delivery_id or self.delivery_ref):
            raise ValueError("delivery_id or delivery_ref must be set for delivery states beyond branch_ready")

        return self


class AttemptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: NonEmptyStr
    issue_id: NonEmptyStr
    run_id: NonEmptyStr
    engine_name: NonEmptyStr
    engine_invocation_id: NonEmptyStr
    engine_capabilities_snapshot: dict[str, Any] = Field(default_factory=dict)
    attempt_state: AttemptState
    progress_type: NonEmptyStr | None = None
    branch_name: NonEmptyStr | None = None
    worktree_path: NonEmptyStr | None = None
    pre_edit_commit_sha: NonEmptyStr | None = None
    preflight_passed: bool | None = None
    preflight_summary: NonEmptyStr | None = None
    engine_outcome: NonEmptyStr | None = None
    validation_result: AttemptValidationResult | None = None
    recoverable: bool | None = None
    retry_recommended: bool | None = None
    summary: NonEmptyStr | None = None
    artifact_dir: NonEmptyStr | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: NonNegativeInt | None = None

    @model_validator(mode="after")
    def validate_attempt_state(self) -> "AttemptRecord":
        if self.attempt_state == AttemptState.accepted:
            if not self._validation_passed():
                raise ValueError("accepted attempts require a passing validation_result")

        if self.attempt_state == AttemptState.preflight_failed and self.preflight_passed is not False:
            raise ValueError("preflight_failed attempts require preflight_passed to be False")

        return self

    def _validation_passed(self) -> bool:
        return self.validation_result is not None and self.validation_result.passed


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: NonEmptyStr
    run_state: RunStateEnum
    base_branch: NonEmptyStr | None = None
    selected_engine_policy: NonEmptyStr | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    issues_attempted: NonNegativeInt = 0
    issues_completed: NonNegativeInt = 0
    issues_blocked: NonNegativeInt = 0
    issues_deferred: NonNegativeInt = 0
    active_issue_id: NonEmptyStr | None = None
    active_attempt_id: NonEmptyStr | None = None
    active_worktrees: list[NonEmptyStr] = Field(default_factory=list)
    alert_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: NonNegativeInt
    run_id: NonEmptyStr
    issue_id: NonEmptyStr | None = None
    attempt_id: NonEmptyStr | None = None
    event_type: NonEmptyStr
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AlertEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: NonEmptyStr
    run_id: NonEmptyStr
    issue_id: NonEmptyStr | None = None
    severity: AlertSeverity
    event_type: NonEmptyStr
    summary: NonEmptyStr
    details: NonEmptyStr | dict[str, Any] | None = None
    created_at: datetime
    delivery_status: NonEmptyStr
