from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
from nightshift.domain.records import AttemptRecord, EventRecord, IssueRecord, RunState
from nightshift.engines.base import EngineCapabilities, EngineOutcome, PreparedInvocation
from nightshift.orchestrator.run_orchestrator import RunOneResult, RunOrchestrator
from nightshift.validation.gate import ValidationResult


def make_contract() -> IssueContract:
    return IssueContract(
        issue_id="ISSUE-1",
        title="Implement run-one",
        kind=IssueKind.execution,
        priority="high",
        goal="Run one issue end to end",
        description="Exercise the orchestrator",
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


def make_issue_record() -> IssueRecord:
    now = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return IssueRecord(
        issue_id="ISSUE-1",
        issue_state=IssueState.ready,
        attempt_state=AttemptState.pending,
        delivery_state=DeliveryState.none,
        queue_priority="high",
        created_at=now,
        updated_at=now,
    )


@dataclass
class FakeWorkspaceHandle:
    branch_name: str = "nightshift/issue-issue-1-implement-run-one"
    worktree_path: Path = Path("/tmp/nightshift/worktree")


@dataclass
class FakeSnapshotHandle:
    pre_edit_commit_sha: str = "abc123"


class FakeIssueRegistry:
    def __init__(self) -> None:
        self.contract = make_contract()
        self.record = make_issue_record()
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

    def attach_attempt(self, issue_id: str, attempt_id: str, attempt_state: AttemptState, run_id: str) -> IssueRecord:
        assert issue_id == self.record.issue_id
        payload = self.record.model_dump(mode="json")
        payload.update(
            {
                "issue_state": IssueState.running,
                "attempt_state": attempt_state,
                "latest_attempt_id": attempt_id,
                "current_run_id": run_id,
            }
        )
        self.record = IssueRecord.model_validate(payload)
        self.saved_records.append(self.record)
        return self.record


class FakeStateStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.saved_run_states: list[RunState] = []
        self.saved_attempt_records: list[AttemptRecord] = []
        self.saved_snapshots: list[tuple[str, IssueRecord]] = []
        self.events: list[EventRecord] = []
        self.active_runs: list[str | None] = []

    def save_run_state(self, run_state: RunState) -> None:
        self.saved_run_states.append(run_state)

    def set_active_run(self, run_id_or_none: str | None) -> None:
        self.active_runs.append(run_id_or_none)

    def save_attempt_record(self, attempt_record: AttemptRecord) -> None:
        self.saved_attempt_records.append(attempt_record)

    def save_run_issue_snapshot(self, run_id: str, issue_record: IssueRecord) -> None:
        self.saved_snapshots.append((run_id, issue_record))

    def append_event(self, event_record: EventRecord) -> None:
        self.events.append(event_record)


class FakeWorkspaceManager:
    def __init__(self) -> None:
        self.workspace = FakeWorkspaceHandle()
        self.snapshot_handle = FakeSnapshotHandle()
        self.rollback_calls = 0

    def prepare_workspace(self, issue_contract: IssueContract) -> FakeWorkspaceHandle:
        assert issue_contract.issue_id == "ISSUE-1"
        return self.workspace

    def snapshot(self, workspace: FakeWorkspaceHandle) -> FakeSnapshotHandle:
        assert workspace == self.workspace
        return self.snapshot_handle

    def rollback(self, workspace: FakeWorkspaceHandle, snapshot: FakeSnapshotHandle) -> None:
        assert workspace == self.workspace
        assert snapshot == self.snapshot_handle
        self.rollback_calls += 1


class FakeAdapter:
    def __init__(self) -> None:
        self.prepared_invocations: list[PreparedInvocation] = []

    def name(self) -> str:
        return "codex"

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(supports_noninteractive_mode=True, supports_worktree_execution=True)

    def prepare(self, issue_contract: IssueContract, workspace: FakeWorkspaceHandle, context_bundle: object) -> PreparedInvocation:
        invocation = PreparedInvocation(
            engine_name="codex",
            invocation_id="invoke-1",
            command=("codex",),
            cwd=workspace.worktree_path,
            artifact_dir=Path("/tmp/nightshift/artifacts/ATTEMPT-1"),
            prompt=issue_contract.title,
            stdout_path=Path("/tmp/nightshift/artifacts/ATTEMPT-1/stdout.txt"),
            stderr_path=Path("/tmp/nightshift/artifacts/ATTEMPT-1/stderr.txt"),
            outcome_path=Path("/tmp/nightshift/artifacts/ATTEMPT-1/engine-outcome.json"),
        )
        self.prepared_invocations.append(invocation)
        return invocation

    def execute(self, prepared_invocation: PreparedInvocation) -> EngineOutcome:
        return EngineOutcome(
            engine_name="codex",
            engine_invocation_id=prepared_invocation.invocation_id,
            outcome_type="success",
            exit_code=0,
            recoverable=False,
            summary="command completed successfully",
            stdout_path=str(prepared_invocation.stdout_path),
            stderr_path=str(prepared_invocation.stderr_path),
            artifact_paths=(str(prepared_invocation.outcome_path),),
        )


class FakeEngineRegistry:
    def __init__(self, adapter: FakeAdapter) -> None:
        self.adapter = adapter

    def resolve(self, issue_contract: IssueContract) -> FakeAdapter:
        assert issue_contract.issue_id == "ISSUE-1"
        return self.adapter


class FakeValidationGate:
    def __init__(self, *, passed: bool) -> None:
        self.result = ValidationResult(
            passed=passed,
            failed_stage=None if passed else "issue_validation",
            stages=(),
            summary="validation passed" if passed else "validation failed",
        )

    def validate(self, issue_contract: IssueContract, workspace: FakeWorkspaceHandle, attempt_record: AttemptRecord) -> ValidationResult:
        assert issue_contract.issue_id == "ISSUE-1"
        assert workspace.worktree_path
        assert attempt_record.issue_id == "ISSUE-1"
        return self.result

    def evaluate_acceptance(self, validation_result: ValidationResult) -> bool:
        return validation_result.passed


def make_orchestrator(*, validation_passed: bool) -> tuple[RunOrchestrator, FakeIssueRegistry, FakeStateStore, FakeWorkspaceManager]:
    issue_registry = FakeIssueRegistry()
    state_store = FakeStateStore(root=Path("/tmp/nightshift"))
    workspace_manager = FakeWorkspaceManager()
    adapter = FakeAdapter()
    engine_registry = FakeEngineRegistry(adapter)
    validation_gate = FakeValidationGate(passed=validation_passed)

    ids = iter(["RUN-1", "ATTEMPT-1"])
    orchestrator = RunOrchestrator(
        issue_registry=issue_registry,
        state_store=state_store,
        workspace_manager=workspace_manager,
        engine_registry=engine_registry,
        validation_gate=validation_gate,
        id_factory=lambda kind: next(ids),
        now_factory=lambda: datetime(2026, 3, 28, tzinfo=timezone.utc),
    )
    return orchestrator, issue_registry, state_store, workspace_manager


def test_run_orchestrator_accepts_issue_and_persists_final_state() -> None:
    orchestrator, issue_registry, state_store, workspace_manager = make_orchestrator(validation_passed=True)

    result = orchestrator.run_one("ISSUE-1")

    assert result == RunOneResult(issue_id="ISSUE-1", run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=True)
    assert issue_registry.record.issue_state == IssueState.done
    assert issue_registry.record.attempt_state == AttemptState.accepted
    assert issue_registry.record.accepted_attempt_id == "ATTEMPT-1"
    assert issue_registry.record.branch_name == workspace_manager.workspace.branch_name
    assert state_store.active_runs == ["RUN-1", None]
    assert state_store.saved_run_states[0].run_state == RunLifecycleState.initializing
    assert state_store.saved_run_states[-1].run_state == RunLifecycleState.completed
    assert state_store.saved_run_states[-1].issues_attempted == 1
    assert state_store.saved_run_states[-1].issues_completed == 1
    assert state_store.saved_attempt_records[-1].attempt_state == AttemptState.accepted
    assert state_store.saved_attempt_records[-1].validation_result is not None
    assert state_store.saved_snapshots[-1][1].issue_state == IssueState.done
    assert workspace_manager.rollback_calls == 0
    assert [event.event_type for event in state_store.events] == [
        "run_started",
        "attempt_started",
        "attempt_finished",
        "run_completed",
    ]


def test_run_orchestrator_rejects_issue_and_rolls_back_workspace() -> None:
    orchestrator, issue_registry, state_store, workspace_manager = make_orchestrator(validation_passed=False)

    result = orchestrator.run_one("ISSUE-1")

    assert result == RunOneResult(issue_id="ISSUE-1", run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=False)
    assert workspace_manager.rollback_calls == 1
    assert issue_registry.record.issue_state == IssueState.ready
    assert issue_registry.record.attempt_state == AttemptState.rejected
    assert issue_registry.record.accepted_attempt_id is None
    assert state_store.saved_attempt_records[-1].attempt_state == AttemptState.rejected
    assert state_store.saved_run_states[-1].issues_completed == 0
    assert state_store.saved_snapshots[-1][1].issue_state == IssueState.ready


def test_run_one_cli_uses_builder_and_prints_result(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text("project:\n  repo_path: .\n  main_branch: main\nrunner:\n  default_engine: codex\n  issue_timeout_seconds: 1\n  overnight_timeout_seconds: 1\nvalidation:\n  enabled: true\nissue_defaults:\n  default_priority: high\n  default_forbidden_paths: [secrets]\n  default_test_edit_policy:\n    can_add_tests: true\n    can_modify_existing_tests: true\n    can_weaken_assertions: false\n    requires_test_change_reason: true\n  default_attempt_limits:\n    max_files_changed: 1\n    max_lines_added: 1\n    max_lines_deleted: 1\n  default_timeouts:\n    command_seconds: 1\n    issue_budget_seconds: 1\nretry:\n  max_retries: 1\n  retry_policy: never\n  failure_circuit_breaker: false\nworkspace:\n  worktree_root: .nightshift/worktrees\n  artifact_root: nightshift-data/runs\nalerts:\n  enabled_channels: []\n  severity_thresholds:\n    info: info\n    warning: warning\n    critical: critical\nreport:\n  output_directory: nightshift-data/reports\n  summary_verbosity: concise\n")

    class FakeCLIOrchestrator:
        def run_one(self, issue_id: str) -> RunOneResult:
            assert issue_id == "ISSUE-1"
            return RunOneResult(issue_id="ISSUE-1", run_id="RUN-CLI", attempt_id="ATTEMPT-CLI", accepted=True)

    monkeypatch.setattr("nightshift.cli.app.build_run_orchestrator", lambda repo, config: FakeCLIOrchestrator())

    result = CliRunner().invoke(
        app,
        ["run-one", "ISSUE-1", "--repo", str(tmp_path), "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert "ISSUE-1" in result.stdout
    assert "RUN-CLI" in result.stdout
    assert "accepted" in result.stdout
