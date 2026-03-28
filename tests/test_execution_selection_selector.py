from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nightshift.domain import AttemptState, DeliveryState, IssueState
from nightshift.domain.records import IssueRecord
from nightshift.product.execution_selection import SelectionError, resolve_all_schedulable_issues, resolve_selected_issues


def make_record(
    issue_id: str,
    *,
    issue_state: IssueState = IssueState.ready,
    queue_priority: str = "high",
) -> IssueRecord:
    now = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return IssueRecord(
        issue_id=issue_id,
        issue_state=issue_state,
        attempt_state=AttemptState.pending,
        delivery_state=DeliveryState.none,
        queue_priority=queue_priority,
        blocker_type="waiting" if issue_state == IssueState.blocked else None,
        created_at=now,
        updated_at=now,
    )


class FakeIssueRegistry:
    def __init__(self, records: list[IssueRecord]) -> None:
        self.records = {record.issue_id: record for record in records}

    def get_record(self, issue_id: str) -> IssueRecord:
        try:
            return self.records[issue_id]
        except KeyError as error:
            raise FileNotFoundError(issue_id) from error

    def list_schedulable_records(self) -> list[IssueRecord]:
        return [record for record in self.records.values() if record.issue_state == IssueState.ready]


def test_resolve_selected_issues_preserves_first_seen_order_and_removes_duplicates() -> None:
    registry = FakeIssueRegistry([make_record("GH-1"), make_record("GH-2"), make_record("GH-3")])

    selection = resolve_selected_issues(registry, ["GH-2", "GH-1", "GH-2", " GH-3 "])

    assert selection.issue_ids == ("GH-2", "GH-1", "GH-3")


def test_resolve_selected_issues_rejects_empty_request() -> None:
    with pytest.raises(SelectionError, match="at least one issue id is required"):
        resolve_selected_issues(FakeIssueRegistry([]), [])


def test_resolve_selected_issues_rejects_unknown_issue_ids_before_execution() -> None:
    registry = FakeIssueRegistry([make_record("GH-1")])

    with pytest.raises(SelectionError, match="unknown issue_id: GH-2"):
        resolve_selected_issues(registry, ["GH-1", "GH-2"])


def test_resolve_selected_issues_rejects_non_schedulable_issue_ids() -> None:
    registry = FakeIssueRegistry([make_record("GH-1"), make_record("GH-2", issue_state=IssueState.blocked)])

    with pytest.raises(SelectionError, match="issue GH-2 is not schedulable"):
        resolve_selected_issues(registry, ["GH-1", "GH-2"])


def test_resolve_all_schedulable_issues_returns_registry_order() -> None:
    registry = FakeIssueRegistry(
        [
            make_record("GH-2", queue_priority="high"),
            make_record("GH-1", queue_priority="urgent"),
            make_record("GH-3", issue_state=IssueState.blocked),
        ]
    )

    selection = resolve_all_schedulable_issues(registry)

    assert selection.issue_ids == ("GH-2", "GH-1")


def test_resolve_all_schedulable_issues_allows_empty_selection() -> None:
    registry = FakeIssueRegistry([make_record("GH-1", issue_state=IssueState.blocked)])

    selection = resolve_all_schedulable_issues(registry)

    assert selection.issue_ids == ()
