from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from nightshift.context.bundle import ContextBundle
from nightshift.domain import AttemptState, DeliveryState, IssueState, RunLifecycleState
from nightshift.domain.records import AttemptRecord, AttemptValidationResult, EventRecord, IssueRecord, RunState


@dataclass(frozen=True, slots=True)
class RunOneResult:
    issue_id: str
    run_id: str
    attempt_id: str
    accepted: bool


class RunOrchestrator:
    def __init__(
        self,
        *,
        issue_registry: Any,
        state_store: Any,
        workspace_manager: Any,
        engine_registry: Any,
        validation_gate: Any,
        id_factory: Callable[[str], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.issue_registry = issue_registry
        self.state_store = state_store
        self.workspace_manager = workspace_manager
        self.engine_registry = engine_registry
        self.validation_gate = validation_gate
        self.id_factory = id_factory or self._default_id_factory
        self.now_factory = now_factory or self._default_now_factory

    def run_one(self, issue_id: str) -> RunOneResult:
        issue_contract = self.issue_registry.get_contract(issue_id)
        current_issue_record = self.issue_registry.get_record(issue_id)

        run_id = self.id_factory("run")
        attempt_id = self.id_factory("attempt")
        started_at = self.now_factory()
        artifact_dir = self._artifact_dir(run_id, attempt_id)
        workspace: Any = None
        snapshot: Any = None
        running_issue_record: IssueRecord | None = None

        self.state_store.save_run_state(
            RunState(
                run_id=run_id,
                run_state=RunLifecycleState.initializing,
                started_at=started_at,
                issues_attempted=1,
                active_issue_id=issue_id,
                active_attempt_id=attempt_id,
            )
        )
        self.state_store.set_active_run(run_id)
        self._append_event(run_id, "run_started", seq=1, issue_id=issue_id)

        try:
            running_issue_record = self.issue_registry.attach_attempt(issue_id, attempt_id, AttemptState.executing, run_id)
            workspace = self.workspace_manager.prepare_workspace(issue_contract)
            snapshot = self.workspace_manager.snapshot(workspace)

            self.state_store.save_run_state(
                RunState(
                    run_id=run_id,
                    run_state=RunLifecycleState.running,
                    started_at=started_at,
                    issues_attempted=1,
                    active_issue_id=issue_id,
                    active_attempt_id=attempt_id,
                    active_worktrees=[str(workspace.worktree_path)],
                )
            )
            self._append_event(run_id, "attempt_started", seq=2, issue_id=issue_id, attempt_id=attempt_id)

            adapter = self.engine_registry.resolve(issue_contract)
            artifact_dir.mkdir(parents=True, exist_ok=True)
            engine_capabilities_snapshot = _capabilities_snapshot(adapter)
            prepared_invocation = adapter.prepare(
                issue_contract,
                workspace,
                ContextBundle(
                    issue_id=issue_id,
                    prompt=self._render_prompt(issue_contract),
                    artifact_dir=artifact_dir,
                    worktree_path=workspace.worktree_path,
                    run_id=run_id,
                    attempt_id=attempt_id,
                ),
            )
            engine_outcome = adapter.execute(prepared_invocation)

            attempt_record = AttemptRecord(
                attempt_id=attempt_id,
                issue_id=issue_id,
                run_id=run_id,
                engine_name=adapter.name(),
                engine_invocation_id=engine_outcome.engine_invocation_id,
                engine_capabilities_snapshot=engine_capabilities_snapshot,
                attempt_state=AttemptState.validating,
                branch_name=workspace.branch_name,
                worktree_path=str(workspace.worktree_path),
                pre_edit_commit_sha=snapshot.pre_edit_commit_sha,
                preflight_passed=True,
                preflight_summary="workspace prepared",
                engine_outcome=engine_outcome.summary,
                recoverable=engine_outcome.recoverable,
                retry_recommended=engine_outcome.recoverable,
                summary=engine_outcome.summary,
                artifact_dir=str(artifact_dir),
                started_at=started_at,
                ended_at=self.now_factory(),
                duration_ms=0,
            )
            self.state_store.save_attempt_record(attempt_record)

            validation_result = self.validation_gate.validate(issue_contract, workspace, attempt_record)
            accepted = bool(self.validation_gate.evaluate_acceptance(validation_result))

            final_attempt = AttemptRecord(
                attempt_id=attempt_id,
                issue_id=issue_id,
                run_id=run_id,
                engine_name=adapter.name(),
                engine_invocation_id=engine_outcome.engine_invocation_id,
                engine_capabilities_snapshot=engine_capabilities_snapshot,
                attempt_state=AttemptState.accepted if accepted else AttemptState.rejected,
                branch_name=workspace.branch_name,
                worktree_path=str(workspace.worktree_path),
                pre_edit_commit_sha=snapshot.pre_edit_commit_sha,
                preflight_passed=True,
                preflight_summary="workspace prepared",
                engine_outcome=engine_outcome.summary,
                validation_result=AttemptValidationResult(
                    passed=validation_result.passed,
                    summary=validation_result.summary,
                    details={"failed_stage": validation_result.failed_stage},
                ),
                recoverable=engine_outcome.recoverable,
                retry_recommended=not accepted,
                summary=validation_result.summary,
                artifact_dir=str(artifact_dir),
                started_at=started_at,
                ended_at=self.now_factory(),
                duration_ms=0,
            )
            self.state_store.save_attempt_record(final_attempt)

            if accepted:
                final_issue_record = self._update_issue_record(
                    running_issue_record,
                    issue_state=IssueState.done,
                    attempt_state=AttemptState.accepted,
                    current_run_id=run_id,
                    latest_attempt_id=attempt_id,
                    accepted_attempt_id=attempt_id,
                    branch_name=workspace.branch_name,
                    worktree_path=str(workspace.worktree_path),
                    last_summary=validation_result.summary,
                )
            else:
                self.workspace_manager.rollback(workspace, snapshot)
                final_issue_record = self._update_issue_record(
                    current_issue_record,
                    issue_state=IssueState.ready,
                    attempt_state=AttemptState.rejected,
                    current_run_id=run_id,
                    latest_attempt_id=attempt_id,
                    accepted_attempt_id=None,
                    branch_name=None,
                    worktree_path=None,
                    last_summary=validation_result.summary,
                )

            self.issue_registry.save_record(final_issue_record)
            self.state_store.save_run_issue_snapshot(run_id, final_issue_record)
            self._append_event(
                run_id,
                "attempt_finished",
                seq=3,
                issue_id=issue_id,
                attempt_id=attempt_id,
                payload={"accepted": accepted},
            )

            self.state_store.save_run_state(
                RunState(
                    run_id=run_id,
                    run_state=RunLifecycleState.completed,
                    started_at=started_at,
                    ended_at=self.now_factory(),
                    issues_attempted=1,
                    issues_completed=1 if accepted else 0,
                )
            )
            self._append_event(run_id, "run_completed", seq=4, issue_id=issue_id, payload={"accepted": accepted})
            return RunOneResult(issue_id=issue_id, run_id=run_id, attempt_id=attempt_id, accepted=accepted)
        except Exception:
            if workspace is not None and snapshot is not None:
                self.workspace_manager.rollback(workspace, snapshot)

            failed_issue_record = self._update_issue_record(
                current_issue_record,
                issue_state=IssueState.ready,
                attempt_state=AttemptState.aborted,
                current_run_id=run_id,
                latest_attempt_id=attempt_id,
                accepted_attempt_id=None,
                branch_name=None,
                worktree_path=None,
                last_summary="run failed",
            )
            self.issue_registry.save_record(failed_issue_record)
            self.state_store.save_run_issue_snapshot(run_id, failed_issue_record)
            self.state_store.save_run_state(
                RunState(
                    run_id=run_id,
                    run_state=RunLifecycleState.aborted,
                    started_at=started_at,
                    ended_at=self.now_factory(),
                    issues_attempted=1,
                )
            )
            self._append_event(run_id, "run_failed", seq=3, issue_id=issue_id, attempt_id=attempt_id)
            raise
        finally:
            self.state_store.set_active_run(None)

    def _update_issue_record(
        self,
        issue_record: IssueRecord,
        *,
        issue_state: IssueState,
        attempt_state: AttemptState,
        current_run_id: str,
        latest_attempt_id: str,
        accepted_attempt_id: str | None,
        branch_name: str | None,
        worktree_path: str | None,
        last_summary: str | None,
    ) -> IssueRecord:
        payload = issue_record.model_dump(mode="json")
        payload.update(
            {
                "issue_state": issue_state,
                "attempt_state": attempt_state,
                "delivery_state": DeliveryState.none,
                "current_run_id": current_run_id,
                "latest_attempt_id": latest_attempt_id,
                "accepted_attempt_id": accepted_attempt_id,
                "branch_name": branch_name,
                "worktree_path": worktree_path,
                "last_summary": last_summary,
                "updated_at": self.now_factory(),
            }
        )
        return IssueRecord.model_validate(payload)

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

    def _artifact_dir(self, run_id: str, attempt_id: str) -> Path:
        return Path(self.state_store.root) / "nightshift-data" / "runs" / run_id / "artifacts" / "attempts" / attempt_id

    def _render_prompt(self, issue_contract: Any) -> str:
        parts = [issue_contract.title, issue_contract.goal]
        if getattr(issue_contract, "description", None):
            parts.append(issue_contract.description)
        if getattr(issue_contract, "acceptance", ()):
            parts.extend(issue_contract.acceptance)
        return "\n\n".join(parts)

    def _default_id_factory(self, kind: str) -> str:
        prefix = "RUN" if kind == "run" else "ATTEMPT"
        return f"{prefix}-{uuid4().hex[:8]}"

    def _default_now_factory(self) -> datetime:
        return datetime.now(timezone.utc)


def _capabilities_snapshot(adapter: Any) -> dict[str, Any]:
    capabilities = getattr(adapter, "capabilities", None)
    if capabilities is None:
        return {}

    value = capabilities()
    if value is None:
        return {}

    if is_dataclass(value):
        return asdict(value)

    try:
        return dict(value)
    except (TypeError, ValueError):
        return {}
