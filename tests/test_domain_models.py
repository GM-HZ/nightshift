import pytest
from pydantic import ValidationError

from nightshift.domain.contracts import IssueContract
from nightshift.domain.records import IssueRecord


def test_issue_contract_rejects_runtime_fields() -> None:
    payload = {
        "issue_id": "ISSUE-1",
        "title": "Implement feature",
        "kind": "task",
        "priority": "high",
        "goal": "Ship the feature",
        "allowed_paths": ["src"],
        "forbidden_paths": ["secrets"],
        "verification": {},
        "test_edit_policy": "allow",
        "attempt_limits": {},
        "timeouts": {},
        "issue_state": "ready",
    }

    with pytest.raises(ValidationError):
        IssueContract.model_validate(payload)


def test_issue_record_exposes_delivery_fields() -> None:
    record = IssueRecord.model_validate(
        {
            "issue_id": "ISSUE-1",
            "issue_state": "draft",
            "attempt_state": "pending",
            "delivery_state": "none",
            "created_at": "2026-03-28T00:00:00Z",
            "updated_at": "2026-03-28T00:00:00Z",
        }
    )

    assert hasattr(record, "queue_priority")
    assert hasattr(record, "delivery_id")
    assert hasattr(record, "delivery_ref")
