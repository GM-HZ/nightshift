from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import AlertSeverity, AttemptState, DeliveryState, IssueState, RunState as RunStateEnum


class IssueRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    issue_state: IssueState
    attempt_state: AttemptState
    delivery_state: DeliveryState
    queue_priority: str
    delivery_id: str | None = None
    delivery_ref: str | None = None
    blocker_type: str | None = None
    progress_type: str | None = None
    current_run_id: str | None = None
    latest_attempt_id: str | None = None
    accepted_attempt_id: str | None = None
    branch_name: str | None = None
    worktree_path: str | None = None
    retry_count: int = 0
    deferred_reason: str | None = None
    last_summary: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_contract(cls, contract: "IssueContract", **data: Any) -> "IssueRecord":
        from .contracts import IssueContract

        if not isinstance(contract, IssueContract):
            raise TypeError("contract must be an IssueContract")

        payload = {"issue_id": contract.issue_id, "queue_priority": contract.priority, **data}
        return cls.model_validate(payload)

    @model_validator(mode="after")
    def validate_delivery_constraints(self) -> "IssueRecord":
        if self.issue_state == IssueState.blocked and not self.blocker_type:
            raise ValueError("blocker_type must be set when issue_state is blocked")

        if self.delivery_state != DeliveryState.none and not self.accepted_attempt_id:
            raise ValueError("accepted_attempt_id must be set when delivery_state is not none")

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

    attempt_id: str
    issue_id: str
    run_id: str
    engine_name: str
    engine_invocation_id: str
    engine_capabilities_snapshot: dict[str, Any] = Field(default_factory=dict)
    attempt_state: AttemptState
    progress_type: str | None = None
    branch_name: str | None = None
    worktree_path: str | None = None
    pre_edit_commit_sha: str | None = None
    preflight_passed: bool | None = None
    preflight_summary: str | None = None
    engine_outcome: str | None = None
    validation_result: dict[str, Any] | None = None
    recoverable: bool | None = None
    retry_recommended: bool | None = None
    summary: str | None = None
    artifact_dir: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None

    @model_validator(mode="after")
    def validate_attempt_state(self) -> "AttemptRecord":
        if self.attempt_state == AttemptState.accepted:
            if not self._validation_passed():
                raise ValueError("accepted attempts require a passing validation_result")

        if self.attempt_state == AttemptState.preflight_failed and self.preflight_passed is not False:
            raise ValueError("preflight_failed attempts require preflight_passed to be False")

        return self

    def _validation_passed(self) -> bool:
        if isinstance(self.validation_result, dict):
            if self.validation_result.get("passed") is True:
                return True
            if self.validation_result.get("success") is True:
                return True
        return False


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    run_state: RunStateEnum
    base_branch: str | None = None
    selected_engine_policy: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    issues_attempted: int = 0
    issues_completed: int = 0
    issues_blocked: int = 0
    issues_deferred: int = 0
    active_issue_id: str | None = None
    active_attempt_id: str | None = None
    active_worktrees: list[str] = Field(default_factory=list)
    alert_counts: dict[str, int] = Field(default_factory=dict)


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int
    run_id: str
    issue_id: str | None = None
    attempt_id: str | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AlertEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    run_id: str
    issue_id: str | None = None
    severity: AlertSeverity
    event_type: str
    summary: str
    details: str | dict[str, Any] | None = None
    created_at: datetime
    delivery_status: str
