from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
from types import SimpleNamespace

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import AttemptState, DeliveryState, IssueKind, IssueState, RunLifecycleState
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
from nightshift.domain.records import AttemptRecord, AttemptValidationResult, IssueRecord, RunState
from nightshift.orchestrator.recovery import RecoveryOrchestrator, RecoveryResult
from nightshift.validation.gate import ValidationResult


def make_contract() -> IssueContract:
    return IssueContract(
        issue_id="ISSUE-1",
        title="Recover interrupted run",
        kind=IssueKind.execution,
        priority="high",
        goal="Restore the run safely",
        description="Exercise recovery flow",
        allowed_paths=("src",),
        forbidden_paths=("secrets",),
        acceptance=("validation passes",),
        engine_preferences=EnginePreferencesContract(primary="codex"),
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=("python -c \"print('ok')\"",),
                pass_condition=PassConditionContract(type="exit_code", expected=0),
            )
        ),
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(command_seconds=30, issue_budget_seconds=300),
    )


def make_issue_record(*, run_id: str, issue_state: IssueState, attempt_state: AttemptState) -> IssueRecord:
    now = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return IssueRecord(
        issue_id="ISSUE-1",
        issue_state=issue_state,
        attempt_state=attempt_state,
        delivery_state=DeliveryState.none,
        queue_priority="high",
        current_run_id=run_id,
        latest_attempt_id="ATTEMPT-1",
        created_at=now,
        updated_at=now,
    )


def make_run_state(run_id: str, *, active_attempt_id: str, active_issue_id: str = "ISSUE-1") -> RunState:
    return RunState.model_validate(
        {
            "run_id": run_id,
            "run_state": "running",
            "base_branch": "main",
            "started_at": "2026-03-28T00:00:00Z",
            "issues_attempted": 1,
            "issues_completed": 0,
            "issues_blocked": 0,
            "issues_deferred": 0,
            "active_issue_id": active_issue_id,
            "active_attempt_id": active_attempt_id,
            "active_worktrees": ["/tmp/worktree"],
            "alert_counts": {},
        }
    )


def make_attempt_record(
    *,
    attempt_id: str,
    run_id: str,
    attempt_state: AttemptState,
    engine_outcome: str | None = None,
    validation_result: AttemptValidationResult | None = None,
) -> AttemptRecord:
    payload: dict[str, object] = {
        "attempt_id": attempt_id,
        "issue_id": "ISSUE-1",
        "run_id": run_id,
        "engine_name": "codex",
        "engine_invocation_id": "INV-1",
        "attempt_state": attempt_state,
        "preflight_passed": True,
        "preflight_summary": "workspace prepared",
        "started_at": "2026-03-28T00:00:00Z",
        "engine_outcome": engine_outcome,
        "validation_result": validation_result.model_dump(mode="json") if validation_result is not None else None,
        "worktree_path": "/tmp/worktree",
        "artifact_dir": "/tmp/artifacts",
    }
    return AttemptRecord.model_validate(payload)


@dataclass
class FakeWorkspace:
    worktree_path: Path = Path("/tmp/worktree")
    branch_name: str = "nightshift/issue-issue-1-recover-interrupted-run"


class FakeIssueRegistry:
    def __init__(self, issue_record: IssueRecord) -> None:
        self.contract = make_contract()
        self.record = issue_record
        self.saved_records: list[IssueRecord] = []

    def get_contract(self, issue_id: str) -> IssueContract:
        assert issue_id == self.contract.issue_id
        return self.contract

    def get_record(self, issue_id: str) -> IssueRecord:
        assert issue_id == self.record.issue_id
        return self.record

    def save_record(self, issue_record: IssueRecord) -> None:
        self.record = issue_record
        self.saved_records.append(issue_record)


class FakeValidationGate:
    def __init__(self, *, passed: bool) -> None:
        self.calls: list[tuple[str, Path, str]] = []
        self.result = ValidationResult(
            passed=passed,
            failed_stage=None if passed else "issue_validation",
            stages=(),
            summary="validation passed" if passed else "validation failed",
        )

    def validate(self, issue_contract: IssueContract, workspace: FakeWorkspace, attempt_record: AttemptRecord) -> ValidationResult:
        self.calls.append((issue_contract.issue_id, workspace.worktree_path, attempt_record.attempt_id))
        return self.result

    def evaluate_acceptance(self, validation_result: ValidationResult) -> bool:
        return validation_result.passed


class FakeStateStore:
    def __init__(self, run_state: RunState, attempt_record: AttemptRecord) -> None:
        self.root = Path("/tmp/nightshift")
        self.run_state = run_state
        self.attempt_record = attempt_record
        self.saved_run_states: list[RunState] = []
        self.saved_attempt_records: list[AttemptRecord] = []
        self.saved_snapshots: list[tuple[str, IssueRecord]] = []
        self.events: list[object] = []
        self.active_runs: list[str | None] = []

    def load_run_state(self, run_id: str) -> RunState:
        assert run_id == self.run_state.run_id
        return self.run_state

    def load_attempt_record(self, attempt_id: str) -> AttemptRecord:
        assert attempt_id == self.attempt_record.attempt_id
        return self.attempt_record

    def save_run_state(self, run_state: RunState) -> None:
        self.saved_run_states.append(run_state)

    def save_attempt_record(self, attempt_record: AttemptRecord) -> None:
        self.attempt_record = attempt_record
        self.saved_attempt_records.append(attempt_record)

    def save_run_issue_snapshot(self, run_id: str, issue_record: IssueRecord) -> None:
        self.saved_snapshots.append((run_id, issue_record))

    def append_event(self, event_record: object) -> None:
        self.events.append(event_record)

    def read_events(self, run_id: str) -> list[object]:
        return [event for event in self.events if getattr(event, "run_id", None) == run_id]

    def set_active_run(self, run_id_or_none: str | None) -> None:
        self.active_runs.append(run_id_or_none)


def make_recovery_orchestrator(
    *,
    run_state: RunState,
    attempt_record: AttemptRecord,
    validation_passed: bool,
    ids: list[str],
) -> tuple[RecoveryOrchestrator, FakeIssueRegistry, FakeStateStore, FakeValidationGate]:
    issue_registry = FakeIssueRegistry(make_issue_record(run_id=run_state.run_id, issue_state=IssueState.running, attempt_state=attempt_record.attempt_state))
    state_store = FakeStateStore(run_state, attempt_record)
    validation_gate = FakeValidationGate(passed=validation_passed)

    iterator = iter(ids)
    orchestrator = RecoveryOrchestrator(
        issue_registry=issue_registry,
        state_store=state_store,
        validation_gate=validation_gate,
        workspace_factory=lambda *_args, **_kwargs: FakeWorkspace(),
        id_factory=lambda kind: next(iterator),
        now_factory=lambda: datetime(2026, 3, 28, tzinfo=timezone.utc),
    )
    return orchestrator, issue_registry, state_store, validation_gate


def test_recovery_marks_source_run_aborted_and_creates_new_run_for_executing_attempt_without_durable_outcome() -> None:
    run_state = make_run_state("run-1", active_attempt_id="ATTEMPT-1")
    attempt_record = make_attempt_record(attempt_id="ATTEMPT-1", run_id="run-1", attempt_state=AttemptState.executing)
    orchestrator, issue_registry, state_store, validation_gate = make_recovery_orchestrator(
        run_state=run_state,
        attempt_record=attempt_record,
        validation_passed=True,
        ids=["recovery-run-1", "recovery-attempt-1"],
    )

    result = orchestrator.recover_run("run-1")

    assert isinstance(result, RecoveryResult)
    assert result.source_run_id == "run-1"
    assert result.recovery_run_id == "recovery-run-1"
    assert result.recovered_attempt_state == AttemptState.aborted
    assert any(saved.run_id == "run-1" and saved.run_state == RunLifecycleState.aborted for saved in state_store.saved_run_states)
    assert any(saved.run_id == "recovery-run-1" for saved in state_store.saved_run_states)
    recovery_run_state = [saved for saved in state_store.saved_run_states if saved.run_id == "recovery-run-1"][-1]
    assert recovery_run_state.active_issue_id is None
    assert recovery_run_state.active_attempt_id is None
    assert state_store.active_runs[-1] is None
    assert validation_gate.calls == []
    assert issue_registry.saved_records[-1].current_run_id == "recovery-run-1"
    assert [(event.run_id, event.seq, event.issue_id, event.attempt_id, event.event_type) for event in state_store.events] == [
        ("run-1", 1, "ISSUE-1", None, "run_recovery_started"),
        ("recovery-run-1", 1, "ISSUE-1", "recovery-attempt-1", "attempt_aborted_on_recovery"),
        ("recovery-run-1", 2, "ISSUE-1", None, "run_recovery_completed"),
    ]


def test_recovery_reruns_validation_for_validating_attempt() -> None:
    run_state = make_run_state("run-1", active_attempt_id="ATTEMPT-1")
    validation_result = AttemptValidationResult(
        passed=True,
        summary="validation passed",
        details={"checks": 1},
    )
    attempt_record = make_attempt_record(
        attempt_id="ATTEMPT-1",
        run_id="run-1",
        attempt_state=AttemptState.validating,
        engine_outcome="normalized engine output",
        validation_result=validation_result,
    )
    orchestrator, issue_registry, state_store, validation_gate = make_recovery_orchestrator(
        run_state=run_state,
        attempt_record=attempt_record,
        validation_passed=True,
        ids=["recovery-run-1", "recovery-attempt-1"],
    )

    result = orchestrator.recover_run("run-1")

    assert isinstance(result, RecoveryResult)
    assert result.source_run_id == "run-1"
    assert result.recovery_run_id == "recovery-run-1"
    assert result.recovered_attempt_state == AttemptState.accepted
    assert validation_gate.calls == [("ISSUE-1", Path("/tmp/worktree"), "recovery-attempt-1")]
    assert any(saved.run_id == "run-1" and saved.run_state == RunLifecycleState.aborted for saved in state_store.saved_run_states)
    assert [saved.attempt_state for saved in state_store.saved_attempt_records] == [
        AttemptState.validating,
        AttemptState.accepted,
    ]
    assert state_store.saved_attempt_records[0].run_id == "recovery-run-1"
    assert state_store.saved_attempt_records[0].attempt_id == "recovery-attempt-1"
    assert state_store.saved_attempt_records[0].artifact_dir == "/tmp/nightshift/nightshift-data/runs/recovery-run-1/artifacts/attempts/recovery-attempt-1"
    assert state_store.saved_snapshots[0][0] == "recovery-run-1"
    assert state_store.saved_snapshots[0][1].issue_state == IssueState.running
    assert issue_registry.saved_records[-1].issue_state == IssueState.done
    final_attempt = state_store.saved_attempt_records[-1]
    assert final_attempt.artifact_dir == "/tmp/nightshift/nightshift-data/runs/recovery-run-1/artifacts/attempts/recovery-attempt-1"
    assert final_attempt.ended_at == datetime(2026, 3, 28, tzinfo=timezone.utc)
    assert final_attempt.duration_ms == 0
    recovery_run_state = [saved for saved in state_store.saved_run_states if saved.run_id == "recovery-run-1"][-1]
    assert recovery_run_state.active_issue_id is None
    assert recovery_run_state.active_attempt_id is None
    assert state_store.active_runs[-1] is None


def test_recovery_defaults_to_runtime_storage_artifact_root_when_available() -> None:
    run_state = make_run_state("run-1", active_attempt_id="ATTEMPT-1")
    validation_result = AttemptValidationResult(
        passed=True,
        summary="validation passed",
        details={"checks": 1},
    )
    attempt_record = make_attempt_record(
        attempt_id="ATTEMPT-1",
        run_id="run-1",
        attempt_state=AttemptState.validating,
        engine_outcome="normalized engine output",
        validation_result=validation_result,
    )
    orchestrator, _issue_registry, state_store, _validation_gate = make_recovery_orchestrator(
        run_state=run_state,
        attempt_record=attempt_record,
        validation_passed=True,
        ids=["recovery-run-1", "recovery-attempt-1"],
    )
    state_store.runtime_storage = SimpleNamespace(artifacts_root=Path("/tmp/runtime-artifacts"))

    orchestrator.recover_run("run-1")

    assert state_store.saved_attempt_records[0].artifact_dir == "/tmp/runtime-artifacts/recovery-run-1/artifacts/attempts/recovery-attempt-1"
    assert state_store.saved_attempt_records[-1].artifact_dir == "/tmp/runtime-artifacts/recovery-run-1/artifacts/attempts/recovery-attempt-1"


def test_recover_command_emits_recovery_run_id(monkeypatch, tmp_path: Path) -> None:
    class FakeRecoveryOrchestrator:
        def recover_run(self, run_id: str) -> RecoveryResult:
            assert run_id == "run-1"
            return RecoveryResult(
                source_run_id="run-1",
                recovery_run_id="recovery-run-1",
                recovered_attempt_id="recovery-attempt-1",
                recovered_attempt_state=AttemptState.aborted,
            )

    monkeypatch.setattr("nightshift.cli.app.build_recovery_orchestrator", lambda repo_root: FakeRecoveryOrchestrator())

    result = CliRunner().invoke(app, ["recover", "--run", "run-1", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["source_run_id"] == "run-1"
    assert payload["recovery_run_id"] == "recovery-run-1"
