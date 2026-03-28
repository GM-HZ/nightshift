from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from nightshift.domain import AttemptState, IssueState, RunLifecycleState
from nightshift.domain.records import AttemptRecord, AttemptValidationResult, EventRecord, IssueRecord, RunState


class RecoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_run_id: str
    recovery_run_id: str
    recovered_attempt_id: str | None = None
    recovered_attempt_state: AttemptState | None = None
    source_run_state: RunLifecycleState = RunLifecycleState.aborted
    recovery_run_state: RunLifecycleState | None = None
    validation_reran: bool = False


class RecoveryOrchestrator:
    def __init__(
        self,
        *,
        issue_registry: Any,
        state_store: Any,
        validation_gate: Any,
        workspace_factory: Callable[[AttemptRecord], Any] | None = None,
        id_factory: Callable[[str], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.issue_registry = issue_registry
        self.state_store = state_store
        self.validation_gate = validation_gate
        self.workspace_factory = workspace_factory or self._default_workspace_factory
        self.id_factory = id_factory or self._default_id_factory
        self.now_factory = now_factory or self._default_now_factory

    def recover_run(self, source_run_id: str) -> RecoveryResult:
        source_run_state = self.state_store.load_run_state(source_run_id)
        if source_run_state.active_attempt_id is None or source_run_state.active_issue_id is None:
            raise ValueError("source run does not have an active issue to recover")

        active_issue_id = source_run_state.active_issue_id
        source_attempt = self.state_store.load_attempt_record(source_run_state.active_attempt_id)
        recovery_run_id = self.id_factory("run")
        recovery_attempt_id = self.id_factory("attempt")
        source_run_ended = self._with_run_state(source_run_state, RunLifecycleState.aborted)
        self.state_store.save_run_state(source_run_ended)
        self._append_event(source_run_id, "run_recovery_started", issue_id=active_issue_id)

        if source_attempt.attempt_state == AttemptState.executing and source_attempt.engine_outcome is None:
            issue_record = self._update_issue_record(
                self.issue_registry.get_record(active_issue_id),
                current_run_id=recovery_run_id,
                latest_attempt_id=recovery_attempt_id,
                issue_state=IssueState.ready,
                attempt_state=AttemptState.aborted,
            )
            self.issue_registry.save_record(issue_record)
            self.state_store.save_run_issue_snapshot(recovery_run_id, issue_record)
            self.state_store.save_attempt_record(
                self._clone_attempt_record(
                    source_attempt,
                    attempt_id=recovery_attempt_id,
                    run_id=recovery_run_id,
                    attempt_state=AttemptState.aborted,
                )
            )
            self.state_store.save_run_state(
                self._with_run_state(
                    self._new_run_state(recovery_run_id, active_issue_id, recovery_attempt_id),
                    RunLifecycleState.aborted,
                )
            )
            self._append_event(
                recovery_run_id,
                "attempt_aborted_on_recovery",
                issue_id=active_issue_id,
                attempt_id=recovery_attempt_id,
            )
            self.state_store.set_active_run(None)
            self._append_event(recovery_run_id, "run_recovery_completed", issue_id=active_issue_id)
            return RecoveryResult(
                source_run_id=source_run_id,
                recovery_run_id=recovery_run_id,
                recovered_attempt_id=recovery_attempt_id,
                recovered_attempt_state=AttemptState.aborted,
                recovery_run_state=RunLifecycleState.aborted,
                validation_reran=False,
            )

        if source_attempt.attempt_state == AttemptState.executing:
            issue_record = self._update_issue_record(
                self.issue_registry.get_record(active_issue_id),
                current_run_id=recovery_run_id,
                latest_attempt_id=recovery_attempt_id,
                issue_state=IssueState.running,
                attempt_state=AttemptState.validating,
            )
            self.issue_registry.save_record(issue_record)
            self.state_store.save_run_issue_snapshot(recovery_run_id, issue_record)
            self.state_store.save_attempt_record(
                self._clone_attempt_record(
                    source_attempt,
                    attempt_id=recovery_attempt_id,
                    run_id=recovery_run_id,
                    attempt_state=AttemptState.validating,
                )
            )
            self.state_store.save_run_state(
                self._with_run_state(
                    self._new_run_state(recovery_run_id, active_issue_id, recovery_attempt_id),
                    RunLifecycleState.running,
                )
            )
            self.state_store.set_active_run(recovery_run_id)
            self._append_event(
                recovery_run_id,
                "attempt_recovered",
                issue_id=active_issue_id,
                attempt_id=recovery_attempt_id,
            )
            self._append_event(recovery_run_id, "run_recovery_completed", issue_id=active_issue_id)
            return RecoveryResult(
                source_run_id=source_run_id,
                recovery_run_id=recovery_run_id,
                recovered_attempt_id=recovery_attempt_id,
                recovered_attempt_state=AttemptState.validating,
                recovery_run_state=RunLifecycleState.running,
                validation_reran=False,
            )

        if source_attempt.attempt_state != AttemptState.validating:
            raise ValueError(f"unsupported recovery state: {source_attempt.attempt_state}")

        issue_contract = self.issue_registry.get_contract(active_issue_id)
        workspace = self.workspace_factory(source_attempt)
        recovery_attempt = self._clone_attempt_record(
            source_attempt,
            attempt_id=recovery_attempt_id,
            run_id=recovery_run_id,
            attempt_state=AttemptState.validating,
        )
        issue_record = self._update_issue_record(
            self.issue_registry.get_record(active_issue_id),
            current_run_id=recovery_run_id,
            latest_attempt_id=recovery_attempt_id,
            issue_state=IssueState.running,
            attempt_state=AttemptState.validating,
        )
        self.issue_registry.save_record(issue_record)
        self.state_store.save_run_issue_snapshot(recovery_run_id, issue_record)
        self.state_store.save_attempt_record(recovery_attempt)
        self.state_store.save_run_state(
            self._with_run_state(
                self._new_run_state(recovery_run_id, active_issue_id, recovery_attempt_id),
                RunLifecycleState.running,
            )
        )
        self.state_store.set_active_run(recovery_run_id)
        self._append_event(
            recovery_run_id,
            "validation_restarted",
            issue_id=active_issue_id,
            attempt_id=recovery_attempt_id,
        )
        validation_result = self.validation_gate.validate(issue_contract, workspace, recovery_attempt)
        accepted = bool(self.validation_gate.evaluate_acceptance(validation_result))

        issue_record = self._update_issue_record(
            self.issue_registry.get_record(active_issue_id),
            current_run_id=recovery_run_id,
            latest_attempt_id=recovery_attempt_id,
            issue_state=IssueState.done if accepted else IssueState.ready,
            attempt_state=AttemptState.accepted if accepted else AttemptState.rejected,
            accepted_attempt_id=recovery_attempt_id if accepted else None,
        )
        self.issue_registry.save_record(issue_record)
        self.state_store.save_run_issue_snapshot(recovery_run_id, issue_record)
        self.state_store.save_attempt_record(
            self._clone_attempt_record(
                recovery_attempt,
                attempt_id=recovery_attempt_id,
                run_id=recovery_run_id,
                attempt_state=AttemptState.accepted if accepted else AttemptState.rejected,
                validation_result=validation_result,
            )
        )
        self.state_store.save_run_state(
            self._with_run_state(
                self._new_run_state(
                    recovery_run_id,
                    active_issue_id,
                    recovery_attempt_id,
                    issues_completed=1 if accepted else 0,
                ),
                RunLifecycleState.completed,
            )
        )
        self.state_store.set_active_run(None)
        self._append_event(recovery_run_id, "run_recovery_completed", issue_id=active_issue_id)
        return RecoveryResult(
            source_run_id=source_run_id,
            recovery_run_id=recovery_run_id,
            recovered_attempt_id=recovery_attempt_id,
            recovered_attempt_state=AttemptState.accepted if accepted else AttemptState.rejected,
            recovery_run_state=RunLifecycleState.completed,
            validation_reran=True,
        )

    def _new_run_state(
        self,
        run_id: str,
        active_issue_id: str,
        active_attempt_id: str,
        *,
        issues_completed: int = 0,
    ) -> RunState:
        return RunState(
            run_id=run_id,
            run_state=RunLifecycleState.running,
            started_at=self.now_factory(),
            issues_attempted=1,
            issues_completed=issues_completed,
            active_issue_id=active_issue_id,
            active_attempt_id=active_attempt_id,
        )

    def _with_run_state(self, run_state: RunState, run_state_value: RunLifecycleState) -> RunState:
        payload = run_state.model_dump(mode="json")
        payload.update(
            {
                "run_state": run_state_value,
                "ended_at": self.now_factory() if run_state_value in {RunLifecycleState.aborted, RunLifecycleState.completed} else None,
            }
        )
        if run_state_value in {RunLifecycleState.aborted, RunLifecycleState.completed}:
            payload.update(
                {
                    "active_issue_id": None,
                    "active_attempt_id": None,
                    "active_worktrees": [],
                }
            )
        return RunState.model_validate(payload)

    def _clone_attempt_record(
        self,
        attempt_record: AttemptRecord,
        *,
        attempt_id: str,
        run_id: str,
        attempt_state: AttemptState,
        validation_result: Any | None = None,
    ) -> AttemptRecord:
        payload = attempt_record.model_dump(mode="json")
        ended_at = self.now_factory() if attempt_state in {AttemptState.accepted, AttemptState.rejected, AttemptState.aborted} else None
        started_at = attempt_record.started_at
        duration_ms: int | None = None
        if started_at is not None and ended_at is not None:
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
        normalized_validation_result: Any | None
        if validation_result is None:
            normalized_validation_result = None
        elif isinstance(validation_result, AttemptValidationResult):
            normalized_validation_result = validation_result.model_dump(mode="json")
        elif hasattr(validation_result, "passed") and hasattr(validation_result, "summary"):
            normalized_validation_result = AttemptValidationResult(
                passed=bool(validation_result.passed),
                summary=getattr(validation_result, "summary", None),
                details={"failed_stage": getattr(validation_result, "failed_stage", None)},
            ).model_dump(mode="json")
        else:
            normalized_validation_result = validation_result
        payload.update(
            {
                "attempt_id": attempt_id,
                "run_id": run_id,
                "attempt_state": attempt_state,
                "artifact_dir": str(self._artifact_dir(run_id, attempt_id)),
                "validation_result": normalized_validation_result,
                "ended_at": ended_at,
                "duration_ms": duration_ms,
            }
        )
        return AttemptRecord.model_validate(payload)

    def _artifact_dir(self, run_id: str, attempt_id: str) -> Path:
        return Path(self.state_store.root) / "nightshift-data" / "runs" / run_id / "artifacts" / "attempts" / attempt_id

    def _update_issue_record(
        self,
        issue_record: IssueRecord,
        *,
        current_run_id: str,
        latest_attempt_id: str,
        issue_state: IssueState,
        attempt_state: AttemptState,
        accepted_attempt_id: str | None = None,
    ) -> IssueRecord:
        payload = issue_record.model_dump(mode="json")
        payload.update(
            {
                "current_run_id": current_run_id,
                "latest_attempt_id": latest_attempt_id,
                "issue_state": issue_state,
                "attempt_state": attempt_state,
                "accepted_attempt_id": accepted_attempt_id,
                "updated_at": self.now_factory(),
            }
        )
        return IssueRecord.model_validate(payload)

    def _append_event(
        self,
        run_id: str,
        event_type: str,
        *,
        issue_id: str | None = None,
        attempt_id: str | None = None,
    ) -> None:
        self.state_store.append_event(
            EventRecord(
                seq=self._next_event_seq(run_id),
                run_id=run_id,
                issue_id=issue_id,
                attempt_id=attempt_id,
                event_type=event_type,
                payload={},
                created_at=self.now_factory(),
            )
        )

    def _next_event_seq(self, run_id: str) -> int:
        events = self.state_store.read_events(run_id)
        if not events:
            return 1
        return max(event.seq for event in events) + 1

    def _default_workspace_factory(self, attempt_record: AttemptRecord) -> Any:
        return Path(attempt_record.worktree_path or ".")

    def _default_id_factory(self, kind: str) -> str:
        prefix = "RUN" if kind == "run" else "ATTEMPT"
        return f"{prefix}-{uuid4().hex[:8]}"

    def _default_now_factory(self) -> datetime:
        return datetime.now(timezone.utc)
