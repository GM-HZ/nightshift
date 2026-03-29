from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
from nightshift.domain.records import IssueRecord, RunState
from nightshift.orchestrator.run_orchestrator import RunOneResult
from nightshift.product.overnight.loop_metadata import DaemonLoopMetadata
from nightshift.product.overnight.service import OvernightControlLoopRequest, OvernightControlLoopService
from nightshift.product.overnight.storage import OvernightLoopMetadataStore


def make_contract() -> IssueContract:
    return IssueContract(
        issue_id="NS-1",
        title="Implement overnight loop",
        kind=IssueKind.execution,
        priority="high",
        goal="Keep executing ready issues overnight",
        description="Exercise the control loop",
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


def make_record(issue_id: str, queue_priority: str = "high") -> IssueRecord:
    now = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return IssueRecord(
        issue_id=issue_id,
        issue_state=IssueState.ready,
        attempt_state=AttemptState.pending,
        delivery_state=DeliveryState.none,
        queue_priority=queue_priority,
        created_at=now,
        updated_at=now,
    )


@dataclass(frozen=True, slots=True)
class FakeSchedulableRecord:
    issue_id: str


class FakeIssueRegistry:
    def __init__(self, schedulable_issue_ids: tuple[str, ...]) -> None:
        self.schedulable_issue_ids = list(schedulable_issue_ids)
        self.contract = make_contract()
        self.saved_records: list[IssueRecord] = []

    def list_schedulable_records(self) -> list[FakeSchedulableRecord]:
        return [FakeSchedulableRecord(issue_id=issue_id) for issue_id in self.schedulable_issue_ids]

    def consume(self, issue_id: str) -> None:
        if issue_id in self.schedulable_issue_ids:
            self.schedulable_issue_ids.remove(issue_id)

    def get_contract(self, issue_id: str) -> IssueContract:
        assert issue_id == self.contract.issue_id
        return self.contract

    def get_record(self, issue_id: str) -> IssueRecord:
        return make_record(issue_id)

    def save_record(self, issue_record: IssueRecord) -> None:
        self.saved_records.append(issue_record)

    def attach_attempt(self, issue_id: str, attempt_id: str, attempt_state: AttemptState, run_id: str) -> IssueRecord:
        return make_record(issue_id)


class FakeEngineRegistry:
    def resolve(self, issue_contract: IssueContract) -> object:
        return object()


class FakeValidationGate:
    def validate(self, issue_contract: IssueContract, workspace: object, attempt_record: object) -> object:
        return type("ValidationResult", (), {"passed": True, "summary": "validation passed", "failed_stage": None})()

    def evaluate_acceptance(self, validation_result: object) -> bool:
        return True


class FakeWorkspaceManager:
    def prepare_workspace(self, issue_contract: IssueContract) -> object:
        return type("Workspace", (), {"branch_name": f"nightshift-{issue_contract.issue_id.lower()}", "worktree_path": Path("/tmp/worktree")})()

    def snapshot(self, workspace: object) -> object:
        return type("Snapshot", (), {"pre_edit_commit_sha": "abc123"})()

    def rollback(self, workspace: object, snapshot: object) -> None:
        return None


class FakeRunOrchestrator:
    def __init__(self, outcomes: dict[str, RunOneResult], registry: FakeIssueRegistry) -> None:
        self.outcomes = outcomes
        self.registry = registry
        self.calls: list[str] = []

    def run_one(self, issue_id: str) -> RunOneResult:
        self.calls.append(issue_id)
        self.registry.consume(issue_id)
        return self.outcomes[issue_id]


def make_state_store(tmp_path: Path):
    from nightshift.store.state_store import StateStore

    return StateStore(tmp_path)


def make_service(state_store):
    return OvernightControlLoopService(state_store=state_store)


def test_daemon_loop_metadata_store_persists_and_marks_stop_requested(tmp_path: Path) -> None:
    state_store = make_state_store(tmp_path)
    store = OvernightLoopMetadataStore(state_store.runtime_storage)
    metadata = DaemonLoopMetadata(
        run_id="DAEMON-1",
        loop_mode="daemon",
        fail_fast=True,
        stop_requested=False,
        created_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
    )

    store.save(metadata)
    loaded = store.load("DAEMON-1")
    assert loaded == metadata

    store.request_stop("DAEMON-1")
    stopped = store.load("DAEMON-1")
    assert stopped.stop_requested is True
    assert stopped.stopped_reason == "user_stop"
    assert (state_store.runtime_storage.runs_root / "DAEMON-1" / "daemon-loop.json").is_file()


def test_daemon_loop_drains_schedulable_issues_in_order(tmp_path: Path) -> None:
    state_store = make_state_store(tmp_path)
    service = make_service(state_store)
    orchestrator = FakeRunOrchestrator(
        {
            "NS-1": RunOneResult(issue_id="NS-1", run_id="RUN-1", attempt_id="ATT-1", accepted=True),
            "NS-2": RunOneResult(issue_id="NS-2", run_id="RUN-2", attempt_id="ATT-2", accepted=True),
        },
        FakeIssueRegistry(("NS-1", "NS-2")),
    )
    registry = orchestrator.registry

    result = service.run(
        orchestrator=orchestrator,
        issue_registry=registry,
        request=OvernightControlLoopRequest(daemon_run_id="DAEMON-1", run_all=True, fail_fast=True),
    )

    assert orchestrator.calls == ["NS-1", "NS-2"]
    assert result.summary.requested == 2
    assert result.summary.completed == 2
    assert result.summary.stopped_early is False
    assert result.summary.stopped_reason == "drained"
    assert result.summary.last_issue_id == "NS-2"
    assert result.summary.last_run_id == "RUN-2"
    assert result.run_state == RunLifecycleState.completed
    assert state_store.load_run_state("DAEMON-1").run_state == RunLifecycleState.completed


def test_daemon_loop_stops_on_first_rejection(tmp_path: Path) -> None:
    state_store = make_state_store(tmp_path)
    service = make_service(state_store)
    orchestrator = FakeRunOrchestrator(
        {
            "NS-1": RunOneResult(issue_id="NS-1", run_id="RUN-1", attempt_id="ATT-1", accepted=True),
            "NS-2": RunOneResult(issue_id="NS-2", run_id="RUN-2", attempt_id="ATT-2", accepted=False),
            "NS-3": RunOneResult(issue_id="NS-3", run_id="RUN-3", attempt_id="ATT-3", accepted=True),
        },
        FakeIssueRegistry(("NS-1", "NS-2", "NS-3")),
    )
    registry = orchestrator.registry

    result = service.run(
        orchestrator=orchestrator,
        issue_registry=registry,
        request=OvernightControlLoopRequest(daemon_run_id="DAEMON-1", run_all=True, fail_fast=True),
    )

    assert orchestrator.calls == ["NS-1", "NS-2"]
    assert result.summary.requested == 2
    assert result.summary.completed == 1
    assert result.summary.stopped_early is True
    assert result.summary.stopped_reason == "failure"
    assert result.summary.failed_issue_id == "NS-2"
    assert result.run_state == RunLifecycleState.aborted


def test_daemon_loop_honors_stop_request_before_next_issue(tmp_path: Path) -> None:
    state_store = make_state_store(tmp_path)
    service = make_service(state_store)
    orchestrator = FakeRunOrchestrator(
        {
            "NS-1": RunOneResult(issue_id="NS-1", run_id="RUN-1", attempt_id="ATT-1", accepted=True),
            "NS-2": RunOneResult(issue_id="NS-2", run_id="RUN-2", attempt_id="ATT-2", accepted=True),
        },
        FakeIssueRegistry(("NS-1", "NS-2")),
    )
    registry = orchestrator.registry

    requested_stop = {"value": False}

    def stop_check() -> bool:
        return requested_stop["value"]

    def flip_stop_after_first(issue_id: str) -> RunOneResult:
        orchestrator.calls.append(issue_id)
        result = orchestrator.outcomes[issue_id]
        requested_stop["value"] = True
        registry.consume(issue_id)
        return result

    orchestrator.run_one = flip_stop_after_first  # type: ignore[method-assign]

    result = service.run(
        orchestrator=orchestrator,
        issue_registry=registry,
        request=OvernightControlLoopRequest(daemon_run_id="DAEMON-1", run_all=True, fail_fast=True),
        stop_check=stop_check,
    )

    assert orchestrator.calls == ["NS-1"]
    assert result.summary.requested == 1
    assert result.summary.completed == 1
    assert result.summary.stopped_early is True
    assert result.summary.stopped_reason == "user_stop"
    assert result.run_state == RunLifecycleState.completed
