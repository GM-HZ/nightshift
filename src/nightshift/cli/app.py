from pathlib import Path
import json
import time
from datetime import datetime, timezone

import typer

from nightshift.config.loader import load_config
from nightshift.domain import AlertSeverity, AttemptState, DeliveryState, IssueState
from nightshift.engines.codex_adapter import CodexAdapter
from nightshift.engines.claude_code_adapter import ClaudeCodeAdapter
from nightshift.engines.registry import EngineRegistry
from nightshift.orchestrator import RunOrchestrator
from nightshift.orchestrator.recovery import RecoveryOrchestrator
from nightshift.product.delivery import DeliveryPRError, open_pull_request
from nightshift.product.queue_admission.service import admit_to_queue
from nightshift.product.work_orders import WorkOrderImportError, import_work_order
from nightshift.registry.issue_registry import IssueRegistry
from nightshift.reporting.minimal_report import build_minimal_report
from nightshift.store.state_store import StateStore
from nightshift.validation import gate as validation_gate
from nightshift.workspace.manager import WorkspaceManager

app = typer.Typer(help="NightShift kernel CLI.")
queue_app = typer.Typer(help="Inspect and mutate the current issue queue.")
issue_app = typer.Typer(help="Import and manage execution issues.")
deliver_app = typer.Typer(help="Move accepted issues through delivery states.")
app.add_typer(queue_app, name="queue")
app.add_typer(issue_app, name="issue")
app.add_typer(deliver_app, name="deliver")


@app.callback(invoke_without_command=True)
def root() -> None:
    pass


def build_run_orchestrator(repo_root: Path, config: object) -> RunOrchestrator:
    adapters = [CodexAdapter(), ClaudeCodeAdapter()]
    return RunOrchestrator(
        issue_registry=IssueRegistry(repo_root),
        state_store=StateStore(repo_root),
        workspace_manager=WorkspaceManager(
            repo_root,
            worktree_root=getattr(config.workspace, "worktree_root", None),
            main_branch=config.project.main_branch,
            cleanup_whitelist=tuple(getattr(config.workspace, "cleanup_whitelist", ())),
        ),
        engine_registry=EngineRegistry(
            adapters,
            default_adapter_name=getattr(config.runner, "default_engine", None),
        ),
        validation_gate=validation_gate,
        artifact_root=getattr(config.workspace, "artifact_root", None),
    )


def build_issue_registry(repo_root: Path) -> IssueRegistry:
    return IssueRegistry(repo_root)


def build_recovery_orchestrator(repo_root: Path) -> RecoveryOrchestrator:
    return RecoveryOrchestrator(
        issue_registry=IssueRegistry(repo_root),
        state_store=StateStore(repo_root),
        validation_gate=validation_gate,
    )


def _resolve_repo_root(repo: Path | None, config: object | None = None) -> Path:
    if repo is not None:
        return repo
    if config is not None:
        configured_repo = getattr(getattr(config, "project", object()), "repo_path", None)
        if configured_repo:
            return Path(configured_repo)
    raise typer.BadParameter("either --repo or a config with project.repo_path is required")


def _write_report_output(report_model: object, config: object | None) -> None:
    if config is None:
        return

    output_directory = getattr(getattr(config, "report", object()), "output_directory", None)
    if not output_directory:
        return

    report_path = Path(output_directory) / f"{getattr(report_model, 'run_id')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_model.model_dump(mode="json"), indent=2))


def _format_queue_add_error(error: Exception) -> str:
    errors = getattr(error, "errors", None)
    if callable(errors):
        try:
            detail_list = errors()
        except Exception:
            detail_list = []
        if detail_list:
            detail = detail_list[0]
            location = ".".join(str(part) for part in detail.get("loc", ()) if part != "__root__")
            message = str(detail.get("msg", "")).strip()
            if location and message.lower() == "field required":
                return f"{location} is required"
            if location and message:
                return f"{location}: {message}"

    message = str(error).strip()
    if message:
        return message.splitlines()[0]
    return error.__class__.__name__


def _resolve_delivery_pr_link(
    *,
    record: object,
    issue_id: str,
    action_name: str,
    pr_ref: str | None,
    pr_id: str | None,
) -> tuple[str | None, str | None]:
    delivery_ref = pr_ref or getattr(record, "delivery_ref", None)
    delivery_id = pr_id or getattr(record, "delivery_id", None)
    if not delivery_ref and not delivery_id:
        typer.echo(
            f"deliver {action_name} failed for {issue_id}: missing PR link; provide --pr-ref/--pr-id or run deliver pr-open first",
            err=True,
        )
        raise typer.Exit(1)
    return delivery_ref, delivery_id


def _run_queue_once(orchestrator: object, issue_registry: IssueRegistry, state_store: StateStore) -> tuple[int, int, int]:
    success_count = 0
    rejected_count = 0
    failed_count = 0
    for record in issue_registry.list_schedulable_records():
        if state_store.is_stop_requested():
            break
        try:
            result = orchestrator.run_one(record.issue_id)
        except Exception as error:
            failed_count += 1
            typer.echo(f"run failed for {record.issue_id}: {error}", err=True)
            continue

        if result.accepted:
            success_count += 1
            typer.echo(f"{result.issue_id} accepted in {result.run_id} ({result.attempt_id})")
        else:
            rejected_count += 1
            typer.echo(f"{result.issue_id} rejected in {result.run_id} ({result.attempt_id})")
    return success_count, rejected_count, failed_count


@app.command("run-one")
def run_one(
    issue_id: str,
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = load_config(config)
    repo_root = _resolve_repo_root(repo, loaded_config)
    orchestrator = build_run_orchestrator(repo_root, loaded_config)
    try:
        result = orchestrator.run_one(issue_id)
    except Exception as error:
        typer.echo(
            f"run-one failed for {issue_id}: {error}. Inspect nightshift-data/runs/ for persisted state and artifacts.",
            err=True,
        )
        raise typer.Exit(1) from error
    status = "accepted" if result.accepted else "rejected"
    typer.echo(f"{result.issue_id} {status} in {result.run_id} ({result.attempt_id})")


@app.command("run")
def run(
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
    daemon: bool = typer.Option(False, "--daemon"),
    poll_seconds: int = typer.Option(30, "--poll-seconds", min=1),
) -> None:
    loaded_config = load_config(config)
    repo_root = _resolve_repo_root(repo, loaded_config)
    orchestrator = build_run_orchestrator(repo_root, loaded_config)
    issue_registry = build_issue_registry(repo_root)
    state_store = StateStore(repo_root)
    state_store.clear_stop_request()

    started_at = datetime.now(timezone.utc)
    timeout_seconds = loaded_config.runner.overnight_timeout_seconds
    accepted_count = 0
    rejected_count = 0
    failed_count = 0
    rounds = 0

    while True:
        rounds += 1
        success, rejected, failed = _run_queue_once(orchestrator, issue_registry, state_store)
        accepted_count += success
        rejected_count += rejected
        failed_count += failed

        if state_store.is_stop_requested():
            typer.echo("stop requested; exiting run loop")
            break

        if not daemon:
            break

        elapsed_seconds = int((datetime.now(timezone.utc) - started_at).total_seconds())
        if elapsed_seconds >= timeout_seconds:
            typer.echo(f"overnight timeout reached after {elapsed_seconds}s; exiting daemon loop")
            break

        time.sleep(poll_seconds)

    typer.echo(
        f"run summary: rounds={rounds} accepted={accepted_count} rejected={rejected_count} failed={failed_count}"
    )


@app.command("stop")
def stop(
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path | None = typer.Option(None, "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = load_config(config) if config is not None else None
    repo_root = _resolve_repo_root(repo, loaded_config)
    state_store = StateStore(repo_root)
    state_store.request_stop()
    active_run = state_store.get_active_run()
    if active_run:
        typer.echo(f"stop requested for active run {active_run}")
    else:
        typer.echo("stop requested; no active run currently set")


@app.command("recover")
def recover(
    run: str = typer.Option(..., "--run"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    orchestrator = build_recovery_orchestrator(repo)
    result = orchestrator.recover_run(run)
    typer.echo(result.model_dump_json(indent=2, exclude_none=True))


@app.command("report")
def report(
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path | None = typer.Option(None, "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
    run: str | None = typer.Option(None, "--run"),
) -> None:
    loaded_config = load_config(config) if config is not None else None
    repo_root = _resolve_repo_root(repo, loaded_config)
    state_store = StateStore(repo_root)
    report_model = build_minimal_report(state_store, run)
    _write_report_output(report_model, loaded_config)
    typer.echo(report_model.model_dump_json(indent=2, exclude_none=True))


@app.command("logs")
def logs(
    issue: str = typer.Option(..., "--issue"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    state_store = StateStore(repo)
    matching_runs: list[dict[str, object]] = []

    for run_state in state_store.list_runs():
        attempts = state_store.list_attempt_records(run_state.run_id, issue_id=issue)
        events = state_store.read_events(run_state.run_id, issue_id=issue)
        if not attempts and not events:
            continue
        matching_runs.append(
            {
                "run_id": run_state.run_id,
                "run_state": run_state.run_state,
                "attempts": [attempt.model_dump(mode="json") for attempt in attempts],
                "events": [event.model_dump(mode="json") for event in events],
            }
        )

    payload = {
        "issue_id": issue,
        "runs": matching_runs,
        "alerts": [alert.model_dump(mode="json") for alert in state_store.read_alerts(issue_id=issue)],
    }
    typer.echo(json.dumps(payload, indent=2))


@app.command("alerts")
def alerts(
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    run: str | None = typer.Option(None, "--run"),
    issue: str | None = typer.Option(None, "--issue"),
    severity: AlertSeverity | None = typer.Option(None, "--severity"),
) -> None:
    state_store = StateStore(repo)
    alert_events = state_store.read_alerts(
        run_id=run,
        issue_id=issue,
        severity=severity,
    )
    payload = {
        "filters": {
            "run_id": run,
            "issue_id": issue,
            "severity": severity.value if severity is not None else None,
        },
        "count": len(alert_events),
        "alerts": [alert.model_dump(mode="json") for alert in alert_events],
    }
    typer.echo(json.dumps(payload, indent=2))


@issue_app.command("import")
def issue_import(
    work_order: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, resolve_path=True),
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
    admit: bool = typer.Option(False, "--admit"),
) -> None:
    loaded_config = load_config(config)
    repo_root = _resolve_repo_root(repo, loaded_config)
    issue_registry = build_issue_registry(repo_root)

    try:
        imported = import_work_order(
            issue_registry,
            config=loaded_config,
            work_order_path=work_order,
            repo_root=repo_root,
        )
    except WorkOrderImportError as error:
        typer.echo(f"issue import failed: {error}", err=True)
        raise typer.Exit(1) from error
    except Exception as error:
        typer.echo(f"issue import failed: {_format_queue_add_error(error)}", err=True)
        raise typer.Exit(1) from error

    record_action = "record_created" if imported.record_created else "record_exists"
    typer.echo(
        f"issue import: {imported.issue_id} imported from {work_order.name} ({record_action})"
    )

    if not admit:
        return

    try:
        admission = admit_to_queue(issue_registry, [imported.issue_id], config=loaded_config)
    except Exception as error:
        typer.echo(f"issue import admit failed for {imported.issue_id}: {_format_queue_add_error(error)}", err=True)
        raise typer.Exit(1) from error

    status = admission.statuses[0]
    if status.status == "already_admitted":
        typer.echo(f"issue import admit: {imported.issue_id} already admitted (priority={status.queue_priority})")
    else:
        typer.echo(f"issue import admit: {imported.issue_id} admitted (priority={status.queue_priority})")


@deliver_app.command("branch-ready")
def deliver_branch_ready(
    issue_id: str,
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    record = issue_registry.get_record(issue_id)
    if record.issue_state != IssueState.done or record.attempt_state != AttemptState.accepted:
        typer.echo(
            f"deliver branch-ready failed for {issue_id}: issue must be done+accepted before delivery",
            err=True,
        )
        raise typer.Exit(1)
    if not record.branch_name:
        typer.echo(
            f"deliver branch-ready failed for {issue_id}: missing branch_name on accepted issue record",
            err=True,
        )
        raise typer.Exit(1)
    updated = issue_registry.attach_delivery(issue_id, DeliveryState.branch_ready)
    typer.echo(f"deliver branch-ready: {updated.issue_id} delivery_state={updated.delivery_state}")


@deliver_app.command("pr-open")
def deliver_pr_open(
    issue_id: str,
    pr_ref: str | None = typer.Option(None, "--pr-ref"),
    pr_id: str | None = typer.Option(None, "--pr-id"),
    auto: bool = typer.Option(False, "--auto"),
    title: str | None = typer.Option(None, "--title"),
    body: str | None = typer.Option(None, "--body"),
    base: str | None = typer.Option(None, "--base"),
    config: Path | None = typer.Option(None, "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    record = issue_registry.get_record(issue_id)
    if record.issue_state != IssueState.done or record.attempt_state != AttemptState.accepted:
        typer.echo(
            f"deliver pr-open failed for {issue_id}: issue must be done+accepted before delivery",
            err=True,
        )
        raise typer.Exit(1)

    if record.delivery_state == DeliveryState.none:
        if not record.branch_name:
            typer.echo(
                f"deliver pr-open failed for {issue_id}: missing branch_name on accepted issue record",
                err=True,
            )
            raise typer.Exit(1)
        issue_registry.attach_delivery(issue_id, DeliveryState.branch_ready)

    if auto:
        loaded_config = load_config(config) if config is not None else None
        contract = issue_registry.get_contract(issue_id)
        base_branch = base or (
            getattr(getattr(loaded_config, "project", object()), "main_branch", None) if loaded_config is not None else None
        )
        base_branch = base_branch or "main"
        pr_title = title or contract.title
        pr_body = body or (
            f"NightShift automated delivery for {issue_id}\n\n"
            f"Goal: {contract.goal}\n"
            f"Accepted attempt: {record.accepted_attempt_id or 'unknown'}"
        )
        try:
            result = open_pull_request(
                repo_root=repo,
                branch_name=record.branch_name or "",
                base_branch=base_branch,
                title=pr_title,
                body=pr_body,
            )
        except DeliveryPRError as error:
            typer.echo(f"deliver pr-open failed for {issue_id}: {error}", err=True)
            raise typer.Exit(1) from error
        pr_ref = result.pr_ref
        pr_id = result.pr_id

    if not pr_ref:
        typer.echo(
            f"deliver pr-open failed for {issue_id}: --pr-ref is required unless --auto is set",
            err=True,
        )
        raise typer.Exit(1)

    updated = issue_registry.attach_delivery(
        issue_id,
        DeliveryState.pr_opened,
        delivery_id=pr_id,
        delivery_ref=pr_ref,
    )
    typer.echo(
        f"deliver pr-open: {updated.issue_id} delivery_state={updated.delivery_state} "
        f"delivery_id={updated.delivery_id} delivery_ref={updated.delivery_ref}"
    )


@deliver_app.command("reviewed")
def deliver_reviewed(
    issue_id: str,
    pr_ref: str | None = typer.Option(None, "--pr-ref"),
    pr_id: str | None = typer.Option(None, "--pr-id"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    record = issue_registry.get_record(issue_id)
    if record.issue_state != IssueState.done or record.attempt_state != AttemptState.accepted:
        typer.echo(
            f"deliver reviewed failed for {issue_id}: issue must be done+accepted before delivery",
            err=True,
        )
        raise typer.Exit(1)
    if record.delivery_state in {DeliveryState.none, DeliveryState.branch_ready}:
        typer.echo(
            f"deliver reviewed failed for {issue_id}: issue must be pr_opened before reviewed",
            err=True,
        )
        raise typer.Exit(1)
    if record.delivery_state in {DeliveryState.merged, DeliveryState.closed_without_merge}:
        typer.echo(
            f"deliver reviewed failed for {issue_id}: issue is already in terminal delivery state {record.delivery_state}",
            err=True,
        )
        raise typer.Exit(1)

    resolved_ref, resolved_id = _resolve_delivery_pr_link(
        record=record,
        issue_id=issue_id,
        action_name="reviewed",
        pr_ref=pr_ref,
        pr_id=pr_id,
    )
    updated = issue_registry.attach_delivery(
        issue_id,
        DeliveryState.reviewed,
        delivery_id=resolved_id,
        delivery_ref=resolved_ref,
    )
    typer.echo(
        f"deliver reviewed: {updated.issue_id} delivery_state={updated.delivery_state} "
        f"delivery_id={updated.delivery_id} delivery_ref={updated.delivery_ref}"
    )


@deliver_app.command("merged")
def deliver_merged(
    issue_id: str,
    pr_ref: str | None = typer.Option(None, "--pr-ref"),
    pr_id: str | None = typer.Option(None, "--pr-id"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    record = issue_registry.get_record(issue_id)
    if record.issue_state != IssueState.done or record.attempt_state != AttemptState.accepted:
        typer.echo(
            f"deliver merged failed for {issue_id}: issue must be done+accepted before delivery",
            err=True,
        )
        raise typer.Exit(1)
    if record.delivery_state in {DeliveryState.none, DeliveryState.branch_ready}:
        typer.echo(
            f"deliver merged failed for {issue_id}: issue must be pr_opened/reviewed before merged",
            err=True,
        )
        raise typer.Exit(1)
    if record.delivery_state == DeliveryState.closed_without_merge:
        typer.echo(
            f"deliver merged failed for {issue_id}: issue is already closed_without_merge",
            err=True,
        )
        raise typer.Exit(1)

    resolved_ref, resolved_id = _resolve_delivery_pr_link(
        record=record,
        issue_id=issue_id,
        action_name="merged",
        pr_ref=pr_ref,
        pr_id=pr_id,
    )
    updated = issue_registry.attach_delivery(
        issue_id,
        DeliveryState.merged,
        delivery_id=resolved_id,
        delivery_ref=resolved_ref,
    )
    typer.echo(
        f"deliver merged: {updated.issue_id} delivery_state={updated.delivery_state} "
        f"delivery_id={updated.delivery_id} delivery_ref={updated.delivery_ref}"
    )


@deliver_app.command("closed-without-merge")
def deliver_closed_without_merge(
    issue_id: str,
    pr_ref: str | None = typer.Option(None, "--pr-ref"),
    pr_id: str | None = typer.Option(None, "--pr-id"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    record = issue_registry.get_record(issue_id)
    if record.issue_state != IssueState.done or record.attempt_state != AttemptState.accepted:
        typer.echo(
            f"deliver closed-without-merge failed for {issue_id}: issue must be done+accepted before delivery",
            err=True,
        )
        raise typer.Exit(1)
    if record.delivery_state in {DeliveryState.none, DeliveryState.branch_ready}:
        typer.echo(
            f"deliver closed-without-merge failed for {issue_id}: issue must be pr_opened/reviewed before close",
            err=True,
        )
        raise typer.Exit(1)
    if record.delivery_state == DeliveryState.merged:
        typer.echo(
            f"deliver closed-without-merge failed for {issue_id}: issue is already merged",
            err=True,
        )
        raise typer.Exit(1)

    resolved_ref, resolved_id = _resolve_delivery_pr_link(
        record=record,
        issue_id=issue_id,
        action_name="closed-without-merge",
        pr_ref=pr_ref,
        pr_id=pr_id,
    )
    updated = issue_registry.attach_delivery(
        issue_id,
        DeliveryState.closed_without_merge,
        delivery_id=resolved_id,
        delivery_ref=resolved_ref,
    )
    typer.echo(
        f"deliver closed-without-merge: {updated.issue_id} delivery_state={updated.delivery_state} "
        f"delivery_id={updated.delivery_id} delivery_ref={updated.delivery_ref}"
    )


@queue_app.command("status")
def queue_status(
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    records = issue_registry.list_schedulable_records()
    if not records:
        typer.echo("no schedulable issues")
        return

    for record in records:
        typer.echo(
            f"{record.issue_id} "
            f"queue_priority={record.queue_priority} "
            f"issue_state={record.issue_state} "
            f"attempt_state={record.attempt_state} "
            f"delivery_state={record.delivery_state}"
        )


@queue_app.command("show")
def queue_show(
    issue_id: str,
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    contract = issue_registry.get_contract(issue_id)
    record = issue_registry.get_record(issue_id)
    context_files = ",".join(contract.context_files)
    typer.echo(
        f"issue_id={record.issue_id} "
        f"priority={contract.priority} "
        f"queue_priority={record.queue_priority} "
        f"issue_state={record.issue_state} "
        f"attempt_state={record.attempt_state} "
        f"delivery_state={record.delivery_state} "
        f"non_goals_count={len(contract.non_goals)} "
        f"context_files={context_files}"
    )


@queue_app.command("add")
def queue_add(
    issue_id: str,
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = load_config(config)
    issue_registry = build_issue_registry(repo)

    try:
        result = admit_to_queue(issue_registry, [issue_id], config=loaded_config)
    except Exception as error:
        typer.echo(f"queue add failed for {issue_id}: {_format_queue_add_error(error)}", err=True)
        raise typer.Exit(1) from error

    status = result.statuses[0]
    if status.status == "already_admitted":
        typer.echo(f"queue add: {issue_id} frozen contract refreshed (priority={status.queue_priority})")
        return

    typer.echo(f"queue add: {issue_id} frozen and admitted to queue (priority={status.queue_priority})")


@queue_app.command("reprioritize")
def queue_reprioritize(
    issue_id: str,
    priority: str,
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    updated = issue_registry.set_queue_priority(issue_id, priority)
    typer.echo(f"{updated.issue_id} queue_priority={updated.queue_priority}")
