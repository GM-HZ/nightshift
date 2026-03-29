from pathlib import Path
import json

import typer

from nightshift.config.loader import load_config
from nightshift.config.loader import load_project_config
from nightshift.config.models import NightShiftConfig
from nightshift.engines.codex_adapter import CodexAdapter
from nightshift.engines.claude_code_adapter import ClaudeCodeAdapter
from nightshift.engines.registry import EngineRegistry
from nightshift.orchestrator import RunOrchestrator
from nightshift.orchestrator.recovery import RecoveryOrchestrator
from nightshift.product.queue_admission.service import admit_to_queue
from nightshift.registry.issue_registry import IssueRegistry
from nightshift.reporting.minimal_report import build_minimal_report
from nightshift.store.state_store import StateStore
from nightshift.validation import gate as validation_gate
from nightshift.workspace.manager import WorkspaceManager

app = typer.Typer(help="NightShift kernel CLI.")
queue_app = typer.Typer(help="Inspect and mutate the current issue queue.")
app.add_typer(queue_app, name="queue")


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
    )


def build_issue_registry(repo_root: Path) -> IssueRegistry:
    return IssueRegistry(repo_root)


def _load_cli_config(
    repo: Path | None,
    config: Path | None,
    *,
    require_repo_config: bool = False,
) -> NightShiftConfig | None:
    if config is not None:
        return load_config(config)
    if repo is not None:
        if (
            (repo / "nightshift.yaml").exists()
            or (repo / ".nightshift/config/migration.yaml").exists()
        ):
            return load_project_config(repo)
        if require_repo_config:
            raise typer.BadParameter("either --config or a repository config is required")
        return None
    return None


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


@app.command("run-one")
def run_one(
    issue_id: str,
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path | None = typer.Option(None, "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = _load_cli_config(repo, config, require_repo_config=True)
    repo_root = _resolve_repo_root(repo, loaded_config)
    orchestrator = build_run_orchestrator(repo_root, loaded_config)
    try:
        result = orchestrator.run_one(issue_id)
    except Exception as error:
        typer.echo(
            f"run-one failed for {issue_id}: {error}. Inspect the runtime runs root (nightshift-data/runs/ for compatibility or .nightshift/runs/ for layered repos) for persisted state and artifacts.",
            err=True,
        )
        raise typer.Exit(1) from error
    status = "accepted" if result.accepted else "rejected"
    typer.echo(f"{result.issue_id} {status} in {result.run_id} ({result.attempt_id})")


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
    loaded_config = _load_cli_config(repo, config)
    repo_root = _resolve_repo_root(repo, loaded_config)
    state_store = StateStore(repo_root)
    report_model = build_minimal_report(state_store, run)
    _write_report_output(report_model, loaded_config)
    typer.echo(report_model.model_dump_json(indent=2, exclude_none=True))


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
    config: Path | None = typer.Option(None, "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = _load_cli_config(repo, config, require_repo_config=True)
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
