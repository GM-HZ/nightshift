from pathlib import Path

import typer

from nightshift.config.loader import load_config
from nightshift.engines.codex_adapter import CodexAdapter
from nightshift.engines.claude_code_adapter import ClaudeCodeAdapter
from nightshift.engines.registry import EngineRegistry
from nightshift.orchestrator import RunOrchestrator
from nightshift.registry.issue_registry import IssueRegistry
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


@app.command("run-one")
def run_one(
    issue_id: str,
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = load_config(config)
    orchestrator = build_run_orchestrator(repo, loaded_config)
    result = orchestrator.run_one(issue_id)
    status = "accepted" if result.accepted else "rejected"
    typer.echo(f"{result.issue_id} {status} in {result.run_id} ({result.attempt_id})")


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
    typer.echo(
        f"issue_id={record.issue_id} "
        f"priority={contract.priority} "
        f"queue_priority={record.queue_priority} "
        f"issue_state={record.issue_state} "
        f"attempt_state={record.attempt_state} "
        f"delivery_state={record.delivery_state}"
    )


@queue_app.command("reprioritize")
def queue_reprioritize(
    issue_id: str,
    priority: str,
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    issue_registry = build_issue_registry(repo)
    updated = issue_registry.set_queue_priority(issue_id, priority)
    typer.echo(f"{updated.issue_id} queue_priority={updated.queue_priority}")
