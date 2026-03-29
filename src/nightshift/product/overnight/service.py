from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from nightshift.domain import RunLifecycleState
from nightshift.domain.records import EventRecord, RunState

from .loop_metadata import DaemonLoopMetadata
from .models import OvernightControlLoopRequest, OvernightControlLoopResult, OvernightControlLoopSummary
from .storage import OvernightLoopMetadataStore


@dataclass(frozen=True, slots=True)
class OvernightControlLoopOutcome:
    issue_id: str
    run_id: str
    accepted: bool
    attempt_id: str


class OvernightControlLoopService:
    def __init__(
        self,
        *,
        state_store: Any,
        metadata_store: OvernightLoopMetadataStore | None = None,
        id_factory: Callable[[str], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.state_store = state_store
        self.metadata_store = metadata_store or OvernightLoopMetadataStore(state_store.runtime_storage)
        self.id_factory = id_factory or self._default_id_factory
        self.now_factory = now_factory or self._default_now_factory

    def request_stop(self, daemon_run_id: str) -> DaemonLoopMetadata:
        return self.metadata_store.request_stop(daemon_run_id)

    def run(
        self,
        *,
        orchestrator: Any,
        issue_registry: Any,
        request: OvernightControlLoopRequest | None = None,
        stop_check: Callable[[], bool] | None = None,
    ) -> OvernightControlLoopResult:
        request = request or OvernightControlLoopRequest()
        if not request.run_all:
            raise ValueError("overnight control loop only supports run_all=True in MVP")

        daemon_run_id = request.daemon_run_id
        fail_fast = request.fail_fast
        loop_run_id = daemon_run_id or self.id_factory("daemon-run")
        started_at = self.now_factory()
        metadata = DaemonLoopMetadata(
            run_id=loop_run_id,
            loop_mode="daemon",
            fail_fast=fail_fast,
            stop_requested=False,
            stopped_reason=None,
            created_at=started_at,
            updated_at=started_at,
        )
        self.metadata_store.save(metadata)
        self.metadata_store.set_active_run(loop_run_id)
        self.state_store.save_run_state(
            RunState(
                run_id=loop_run_id,
                run_state=RunLifecycleState.running,
                started_at=started_at,
                issues_attempted=0,
                issues_completed=0,
            )
        )
        self._append_event(loop_run_id, "daemon_started", seq=1, payload={"fail_fast": fail_fast})

        outcomes: list[OvernightControlLoopOutcome] = []
        issues_attempted = 0
        issues_completed = 0
        stopped_reason = "none"
        stopped_early = False
        failed_issue_id: str | None = None

        try:
            while True:
                if self._is_stop_requested(loop_run_id, stop_check):
                    stopped_reason = "user_stop"
                    stopped_early = True
                    self._append_event(loop_run_id, "daemon_stop_requested", seq=self._next_seq(loop_run_id))
                    self.state_store.save_run_state(
                        RunState(
                            run_id=loop_run_id,
                            run_state=RunLifecycleState.stopping,
                            started_at=started_at,
                            issues_attempted=issues_attempted,
                            issues_completed=issues_completed,
                        )
                    )
                    break

                schedulable_records = list(issue_registry.list_schedulable_records())
                if not schedulable_records:
                    stopped_reason = "drained"
                    self._append_event(loop_run_id, "daemon_drained", seq=self._next_seq(loop_run_id))
                    break

                issue_id = schedulable_records[0].issue_id
                self._append_event(
                    loop_run_id,
                    "daemon_issue_selected",
                    seq=self._next_seq(loop_run_id),
                    issue_id=issue_id,
                )

                run_result = orchestrator.run_one(issue_id)
                if run_result.issue_id != issue_id:
                    raise ValueError("run_one returned a mismatched issue id")

                outcome = OvernightControlLoopOutcome(
                    issue_id=run_result.issue_id,
                    run_id=run_result.run_id,
                    accepted=run_result.accepted,
                    attempt_id=run_result.attempt_id,
                )
                outcomes.append(outcome)
                issues_attempted += 1
                issues_completed += 1 if run_result.accepted else 0
                failed_issue_id = None if run_result.accepted else issue_id

                metadata = self._update_metadata(
                    metadata,
                    stop_requested=self._is_stop_requested(loop_run_id, stop_check),
                    stopped_reason=stopped_reason,
                    issues_attempted=issues_attempted,
                    issues_completed=issues_completed,
                    last_issue_id=issue_id,
                    last_run_id=run_result.run_id,
                    failed_issue_id=failed_issue_id,
                )
                self.metadata_store.save(metadata)

                self._append_event(
                    loop_run_id,
                    "daemon_issue_finished",
                    seq=self._next_seq(loop_run_id),
                    issue_id=issue_id,
                    attempt_id=run_result.attempt_id,
                    payload={"accepted": run_result.accepted},
                )

                if not run_result.accepted and fail_fast:
                    stopped_reason = "failure"
                    stopped_early = True
                    self.state_store.save_run_state(
                        RunState(
                            run_id=loop_run_id,
                            run_state=RunLifecycleState.aborted,
                            started_at=started_at,
                            issues_attempted=issues_attempted,
                            issues_completed=issues_completed,
                        )
                    )
                    self._append_event(
                        loop_run_id,
                        "daemon_failed",
                        seq=self._next_seq(loop_run_id),
                        issue_id=issue_id,
                        attempt_id=run_result.attempt_id,
                    )
                    break

            run_state = RunLifecycleState.aborted if stopped_reason == "failure" else RunLifecycleState.completed
            self.state_store.save_run_state(
                RunState(
                    run_id=loop_run_id,
                    run_state=run_state,
                    started_at=started_at,
                    ended_at=self.now_factory(),
                    issues_attempted=issues_attempted,
                    issues_completed=issues_completed,
                )
            )
            metadata = self._update_metadata(
                metadata,
                stop_requested=self._is_stop_requested(loop_run_id, stop_check) or stopped_reason == "user_stop",
                stopped_reason=stopped_reason,
                issues_attempted=issues_attempted,
                issues_completed=issues_completed,
                last_issue_id=outcomes[-1].issue_id if outcomes else None,
                last_run_id=outcomes[-1].run_id if outcomes else None,
                failed_issue_id=failed_issue_id,
            )
            self.metadata_store.save(metadata)
            self._append_event(
                loop_run_id,
                "daemon_completed",
                seq=self._next_seq(loop_run_id),
                payload={"run_state": run_state.value, "stopped_reason": stopped_reason},
            )
            return OvernightControlLoopResult(
                daemon_run_id=loop_run_id,
                run_state=run_state,
                started_at=started_at,
                ended_at=self.now_factory(),
                outcomes=tuple(asdict(outcome) for outcome in outcomes),
                summary=OvernightControlLoopSummary(
                    requested=issues_attempted,
                    completed=issues_completed,
                    stopped_early=stopped_early,
                    stopped_reason=stopped_reason,
                    last_issue_id=outcomes[-1].issue_id if outcomes else None,
                    last_run_id=outcomes[-1].run_id if outcomes else None,
                    failed_issue_id=failed_issue_id,
                ),
                metadata=metadata,
            )
        finally:
            self.metadata_store.set_active_run(None)

    def _is_stop_requested(
        self,
        daemon_run_id: str,
        stop_check: Callable[[], bool] | None,
    ) -> bool:
        if stop_check is not None and stop_check():
            return True
        try:
            return self.metadata_store.load(daemon_run_id).stop_requested
        except FileNotFoundError:
            return False

    def _update_metadata(
        self,
        metadata: DaemonLoopMetadata,
        *,
        stop_requested: bool,
        stopped_reason: str,
        issues_attempted: int,
        issues_completed: int,
        last_issue_id: str | None = None,
        last_run_id: str | None = None,
        failed_issue_id: str | None = None,
    ) -> DaemonLoopMetadata:
        payload = metadata.model_dump(mode="json")
        payload.update(
            {
                "stop_requested": stop_requested,
                "stopped_reason": stopped_reason if stopped_reason != "none" else None,
                "issues_attempted": issues_attempted,
                "issues_completed": issues_completed,
                "last_issue_id": last_issue_id,
                "last_run_id": last_run_id,
                "failed_issue_id": failed_issue_id,
                "updated_at": self.now_factory(),
            }
        )
        return DaemonLoopMetadata.model_validate(payload)

    def _append_event(
        self,
        run_id: str,
        event_type: str,
        *,
        seq: int,
        issue_id: str | None = None,
        attempt_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.state_store.append_event(
            EventRecord(
                seq=seq,
                run_id=run_id,
                issue_id=issue_id,
                attempt_id=attempt_id,
                event_type=event_type,
                payload=payload or {},
                created_at=self.now_factory(),
            )
        )

    def _next_seq(self, run_id: str) -> int:
        try:
            return len(self.state_store.read_events(run_id)) + 1
        except Exception:
            return 1

    def _default_id_factory(self, kind: str) -> str:
        prefix = "DAEMON" if kind == "daemon-run" else kind.upper()
        return f"{prefix}-{uuid4().hex[:8]}"

    def _default_now_factory(self) -> datetime:
        return datetime.now(timezone.utc)
