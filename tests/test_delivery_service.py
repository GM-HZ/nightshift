from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from nightshift.domain import AttemptState, DeliveryState, IssueState
from nightshift.domain.records import AttemptRecord, IssueRecord
from nightshift.product.delivery.github_client import (
    GitHubPullRequestClient,
    GitHubPullRequestClientError,
    resolve_delivery_github_token,
)
from nightshift.product.delivery.models import DeliveryBatchRequest
from nightshift.product.delivery.service import (
    DeliveryEligibility,
    DeliveryServiceError,
    DeliveryWriteResult,
    deliver_issue,
    evaluate_delivery_eligibility,
)


def make_issue_record(
    *,
    issue_id: str = "GH-7",
    issue_state: IssueState = IssueState.done,
    attempt_state: AttemptState = AttemptState.accepted,
    delivery_state: DeliveryState = DeliveryState.branch_ready,
    accepted_attempt_id: str | None = "ATTEMPT-1",
) -> IssueRecord:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return IssueRecord.model_validate(
        {
            "issue_id": issue_id,
            "issue_state": issue_state,
            "attempt_state": attempt_state,
            "delivery_state": delivery_state,
            "queue_priority": "high",
            "accepted_attempt_id": accepted_attempt_id,
            "latest_attempt_id": accepted_attempt_id,
            "branch_name": "nightshift-issue-gh-7-readme",
            "worktree_path": "/tmp/nightshift/worktree",
            "created_at": now,
            "updated_at": now,
        }
    )


def make_attempt_record(*, issue_id: str = "GH-7", run_id: str = "RUN-1", attempt_id: str = "ATTEMPT-1") -> AttemptRecord:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return AttemptRecord.model_validate(
        {
            "attempt_id": attempt_id,
            "issue_id": issue_id,
            "run_id": run_id,
            "engine_name": "codex",
            "engine_invocation_id": "invoke-1",
            "attempt_state": AttemptState.accepted,
            "engine_outcome": "command completed successfully",
            "validation_result": {
                "passed": True,
                "summary": "validation passed",
            },
            "branch_name": "nightshift-issue-gh-7-readme",
            "worktree_path": "/tmp/nightshift/worktree",
            "pre_edit_commit_sha": "abc123",
            "artifact_dir": f"/tmp/nightshift/artifacts/runs/{run_id}/attempts/{attempt_id}",
            "started_at": now,
            "ended_at": now,
            "duration_ms": 0,
        }
    )


def write_delivery_snapshot(root: Path, *, issue_id: str = "GH-7", run_id: str = "RUN-1", attempt_id: str = "ATTEMPT-1") -> Path:
    snapshot_path = root / "artifacts" / "runs" / run_id / "attempts" / attempt_id / "delivery" / "snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(
            {
                "issue_id": issue_id,
                "run_id": run_id,
                "attempt_id": attempt_id,
                "work_order_id": "WO-GH-7",
                "work_order_revision": "rev-1",
                "contract_revision": "rev-1",
                "delivery_state": "branch_ready",
                "branch_name": "nightshift-issue-gh-7-readme",
                "worktree_path": "/tmp/nightshift/worktree",
                "pre_edit_commit_sha": "abc123",
            }
        )
    )
    return snapshot_path


def test_delivery_batch_request_requires_issue_ids() -> None:
    with pytest.raises(ValueError):
        DeliveryBatchRequest(issue_ids=())


def test_evaluate_delivery_eligibility_accepts_branch_ready_issue_with_snapshot(tmp_path: Path) -> None:
    record = make_issue_record()
    attempt = make_attempt_record()
    snapshot_path = write_delivery_snapshot(tmp_path)

    eligibility = evaluate_delivery_eligibility(
        record,
        attempt,
        snapshot_root=tmp_path / "artifacts",
    )

    assert isinstance(eligibility, DeliveryEligibility)
    assert eligibility.issue_id == "GH-7"
    assert eligibility.snapshot_path == snapshot_path


def test_evaluate_delivery_eligibility_rejects_mismatched_accepted_attempt() -> None:
    record = make_issue_record(accepted_attempt_id="ATTEMPT-2")
    attempt = make_attempt_record()

    with pytest.raises(DeliveryServiceError, match="accepted attempt mismatch"):
        evaluate_delivery_eligibility(record, attempt, snapshot_root=Path("/tmp/nightshift/artifacts"))


def test_evaluate_delivery_eligibility_rejects_non_deliverable_issue_state(tmp_path: Path) -> None:
    record = make_issue_record(issue_state=IssueState.ready, attempt_state=AttemptState.pending, delivery_state=DeliveryState.none)
    attempt = make_attempt_record()
    write_delivery_snapshot(tmp_path)

    with pytest.raises(DeliveryServiceError, match="not deliverable"):
        evaluate_delivery_eligibility(record, attempt, snapshot_root=tmp_path / "artifacts")


def test_evaluate_delivery_eligibility_rejects_missing_snapshot(tmp_path: Path) -> None:
    record = make_issue_record()
    attempt = make_attempt_record()

    with pytest.raises(DeliveryServiceError, match="missing accepted delivery snapshot"):
        evaluate_delivery_eligibility(record, attempt, snapshot_root=tmp_path / "artifacts")


class FakeIssueRegistry:
    def __init__(self, record: IssueRecord) -> None:
        self.record = record
        self.attach_calls: list[tuple[DeliveryState, str | None, str | None]] = []

    def get_record(self, issue_id: str) -> IssueRecord:
        assert issue_id == self.record.issue_id
        return self.record

    def attach_delivery(
        self,
        issue_id: str,
        delivery_state: DeliveryState,
        delivery_id: str | None = None,
        delivery_ref: str | None = None,
    ) -> IssueRecord:
        assert issue_id == self.record.issue_id
        self.attach_calls.append((delivery_state, delivery_id, delivery_ref))
        payload = self.record.model_dump(mode="json")
        payload.update(
            {
                "delivery_state": delivery_state,
                "delivery_id": delivery_id,
                "delivery_ref": delivery_ref,
            }
        )
        self.record = IssueRecord.model_validate(payload)
        return self.record


class FakeStateStore:
    def __init__(self, attempt: AttemptRecord) -> None:
        self.attempt = attempt

    def load_attempt_record(self, attempt_id: str) -> AttemptRecord:
        assert attempt_id == self.attempt.attempt_id
        return self.attempt


def test_deliver_issue_updates_delivery_linkage_from_snapshot(tmp_path: Path) -> None:
    record = make_issue_record()
    attempt = make_attempt_record()
    registry = FakeIssueRegistry(record)
    state_store = FakeStateStore(attempt)
    snapshot_path = write_delivery_snapshot(tmp_path)

    observed: dict[str, object] = {}

    def fake_push(*, snapshot: dict[str, object]) -> None:
        observed["snapshot"] = snapshot

    def fake_create_pr(*, issue_record: IssueRecord, snapshot: dict[str, object]) -> DeliveryWriteResult:
        observed["issue_record"] = issue_record.issue_id
        return DeliveryWriteResult(
            issue_id=issue_record.issue_id,
            delivery_state=DeliveryState.pr_opened,
            delivery_id="8",
            delivery_ref="https://github.com/GM-HZ/nightshift/pull/8",
        )

    result = deliver_issue(
        "GH-7",
        issue_registry=registry,
        state_store=state_store,
        snapshot_root=tmp_path / "artifacts",
        push_delivery=fake_push,
        create_pr=fake_create_pr,
    )

    assert snapshot_path.exists()
    assert result.delivery_state == DeliveryState.pr_opened
    assert result.delivery_id == "8"
    assert registry.record.delivery_state == DeliveryState.pr_opened
    assert registry.record.delivery_ref == "https://github.com/GM-HZ/nightshift/pull/8"
    assert observed["issue_record"] == "GH-7"
    assert observed["snapshot"]["attempt_id"] == "ATTEMPT-1"


def test_deliver_issue_preserves_branch_ready_when_pr_create_fails(tmp_path: Path) -> None:
    record = make_issue_record()
    attempt = make_attempt_record()
    registry = FakeIssueRegistry(record)
    state_store = FakeStateStore(attempt)
    write_delivery_snapshot(tmp_path)

    def fake_push(*, snapshot: dict[str, object]) -> None:
        return None

    def fail_create_pr(*, issue_record: IssueRecord, snapshot: dict[str, object]) -> DeliveryWriteResult:
        raise RuntimeError("github create failed")

    with pytest.raises(DeliveryServiceError, match="github create failed"):
        deliver_issue(
            "GH-7",
            issue_registry=registry,
            state_store=state_store,
            snapshot_root=tmp_path / "artifacts",
            push_delivery=fake_push,
            create_pr=fail_create_pr,
        )

    assert registry.record.delivery_state == DeliveryState.branch_ready
    assert registry.record.delivery_id is None
    assert registry.record.delivery_ref is None


def test_resolve_delivery_github_token_prefers_nightshift_specific_variable(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTSHIFT_GITHUB_TOKEN", "nightshift-token")
    monkeypatch.setenv("GITHUB_TOKEN", "generic-token")

    assert resolve_delivery_github_token() == "nightshift-token"


def test_resolve_delivery_github_token_rejects_missing_token(monkeypatch) -> None:
    monkeypatch.delenv("NIGHTSHIFT_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(GitHubPullRequestClientError, match="missing GitHub token"):
        resolve_delivery_github_token()


def test_github_pull_request_client_creates_pr_and_normalizes_result(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "number": 8,
                    "html_url": "https://github.com/GM-HZ/nightshift/pull/8",
                }
            ).encode("utf-8")

    def fake_urlopen(request):
        observed["url"] = request.full_url
        observed["auth"] = request.headers["Authorization"]
        observed["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = GitHubPullRequestClient(token="test-token")
    result = client.create_pull_request(
        repo_full_name="GM-HZ/nightshift",
        title="docs: add zh readme",
        body="from NightShift",
        head="nightshift-issue-gh-7-readme",
        base="master",
        issue_id="GH-7",
    )

    assert observed["url"] == "https://api.github.com/repos/GM-HZ/nightshift/pulls"
    assert observed["auth"] == "Bearer test-token"
    assert observed["body"]["title"] == "docs: add zh readme"
    assert result.issue_id == "GH-7"
    assert result.delivery_id == "8"
    assert result.delivery_ref == "https://github.com/GM-HZ/nightshift/pull/8"


def test_github_pull_request_client_surfaces_create_failure_cleanly(monkeypatch) -> None:
    def fake_urlopen(request):
        raise OSError("network down")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = GitHubPullRequestClient(token="test-token")
    with pytest.raises(GitHubPullRequestClientError, match="failed to create pull request"):
        client.create_pull_request(
            repo_full_name="GM-HZ/nightshift",
            title="docs: add zh readme",
            body="from NightShift",
            head="nightshift-issue-gh-7-readme",
            base="master",
            issue_id="GH-7",
        )
