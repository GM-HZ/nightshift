from nightshift.orchestrator.run_orchestrator import RunOneResult
from nightshift.product.execution_selection import BatchRunSummary, SelectionItem, SelectionResult, run_batch


def test_run_batch_executes_all_selected_issues_in_order() -> None:
    calls: list[str] = []

    def fake_run_one(issue_id: str) -> RunOneResult:
        calls.append(issue_id)
        return RunOneResult(issue_id=issue_id, run_id=f"RUN-{issue_id}", attempt_id=f"ATT-{issue_id}", accepted=True)

    summary = run_batch(
        SelectionResult(items=(SelectionItem(issue_id="GH-1", queue_priority="high"), SelectionItem(issue_id="GH-2", queue_priority="low"))),
        fake_run_one,
    )

    assert calls == ["GH-1", "GH-2"]
    assert summary == BatchRunSummary(batch_size=2, issues_attempted=2, issues_accepted=2, stopped_early=False)


def test_run_batch_stops_after_first_failure() -> None:
    calls: list[str] = []

    def fake_run_one(issue_id: str) -> RunOneResult:
        calls.append(issue_id)
        return RunOneResult(
            issue_id=issue_id,
            run_id=f"RUN-{issue_id}",
            attempt_id=f"ATT-{issue_id}",
            accepted=issue_id != "GH-2",
        )

    summary = run_batch(
        SelectionResult(
            items=(
                SelectionItem(issue_id="GH-1", queue_priority="high"),
                SelectionItem(issue_id="GH-2", queue_priority="high"),
                SelectionItem(issue_id="GH-3", queue_priority="high"),
            )
        ),
        fake_run_one,
    )

    assert calls == ["GH-1", "GH-2"]
    assert summary == BatchRunSummary(
        batch_size=3,
        issues_attempted=2,
        issues_accepted=1,
        stopped_early=True,
        first_failure_issue_id="GH-2",
    )


def test_run_batch_handles_empty_selection_without_invoking_run_one() -> None:
    calls: list[str] = []

    def fake_run_one(issue_id: str) -> RunOneResult:
        calls.append(issue_id)
        raise AssertionError("should not be called")

    summary = run_batch(SelectionResult(), fake_run_one)

    assert calls == []
    assert summary == BatchRunSummary(batch_size=0, issues_attempted=0, issues_accepted=0, stopped_early=False)
