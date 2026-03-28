from pathlib import Path
import json

import typer

from nightshift.config.loader import load_config
from nightshift.engines.codex_adapter import CodexAdapter
from nightshift.engines.claude_code_adapter import ClaudeCodeAdapter
from nightshift.engines.registry import EngineRegistry
from nightshift.orchestrator import RunOrchestrator
from nightshift.orchestrator.recovery import RecoveryOrchestrator
from nightshift.product.execution_selection import resolve_all_schedulable_issues, resolve_selected_issues, run_batch
from nightshift.product.issue_ingestion import (
    check_issue_admission,
    check_issue_provenance,
    fetch_github_issue,
    materialize_issue,
    parse_github_issue_template,
)
from nightshift.product.queue_admission import admit_to_queue
from nightshift.product.splitter import (
    ProposalStore,
    approve_proposals,
    create_github_issue,
    publish_proposals,
    reject_proposals,
    split_requirement_file,
    update_proposals,
)
from nightshift.registry.issue_registry import IssueRegistry
from nightshift.reporting.minimal_report import build_minimal_report
from nightshift.store.state_store import StateStore
from nightshift.validation import gate as validation_gate
from nightshift.workspace.manager import WorkspaceManager

app = typer.Typer(help="NightShift kernel CLI.")
queue_app = typer.Typer(help="Inspect and mutate the current issue queue.")
issue_app = typer.Typer(help="Ingest product-layer issues into the NightShift kernel queue.")
proposals_app = typer.Typer(help="Inspect and publish splitter proposal batches.")
app.add_typer(queue_app, name="queue")
app.add_typer(issue_app, name="issue")
app.add_typer(proposals_app, name="proposals")


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


def _build_proposal_store(repo_root: Path) -> ProposalStore:
    return ProposalStore(repo_root)


@app.command("split")
def split(
    file: Path = typer.Option(..., "--file", exists=True, dir_okay=False, readable=True, resolve_path=True),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    store = _build_proposal_store(repo)
    batch = split_requirement_file(file)
    store.save_batch(batch)
    typer.echo(f"created proposal batch {batch.batch_id} with {len(batch.proposals)} proposal(s)")


@proposals_app.command("show")
def proposals_show(
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    store = _build_proposal_store(repo)
    batches = store.list_batches()
    if not batches:
        typer.echo("no proposal batches")
        return
    for batch in batches:
        typer.echo(f"batch_id={batch.batch_id} source={batch.source_requirement_path}")
        for proposal in batch.proposals:
            typer.echo(
                f"proposal_id={proposal.proposal_id} title={proposal.title} review_status={proposal.review_status}"
            )


@proposals_app.command("publish")
def proposals_publish(
    proposal_ids: list[str] = typer.Argument(...),
    batch: str = typer.Option(..., "--batch"),
    repo_full_name: str = typer.Option(..., "--repo-full-name"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    store = _build_proposal_store(repo)
    try:
        _, refs = publish_proposals(
            store,
            batch,
            proposal_ids,
            repo_full_name=repo_full_name,
            publisher=create_github_issue,
        )
    except Exception as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    for proposal_id, ref in zip(proposal_ids, refs):
        typer.echo(f"published proposal {proposal_id} as {ref.repo_full_name}#{ref.issue_number}")


@proposals_app.command("approve")
def proposals_approve(
    proposal_ids: list[str] = typer.Argument(...),
    batch: str = typer.Option(..., "--batch"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    store = _build_proposal_store(repo)
    try:
        updated = approve_proposals(store, batch, proposal_ids)
    except Exception as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    selected = set(proposal_ids)
    for proposal in updated.proposals:
        if proposal.proposal_id in selected:
            typer.echo(f"approved proposal {proposal.proposal_id}")


@proposals_app.command("reject")
def proposals_reject(
    proposal_ids: list[str] = typer.Argument(...),
    batch: str = typer.Option(..., "--batch"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
) -> None:
    store = _build_proposal_store(repo)
    try:
        updated = reject_proposals(store, batch, proposal_ids)
    except Exception as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    selected = set(proposal_ids)
    for proposal in updated.proposals:
        if proposal.proposal_id in selected:
            typer.echo(f"rejected proposal {proposal.proposal_id}")


@proposals_app.command("update")
def proposals_update(
    proposal_ids: list[str] = typer.Argument(...),
    batch: str = typer.Option(..., "--batch"),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    allowed_paths: list[str] = typer.Option([], "--allowed-path"),
    acceptance_criteria: list[str] = typer.Option([], "--acceptance"),
    verification_commands: list[str] = typer.Option([], "--verify"),
    clear_missing_context: bool = typer.Option(False, "--clear-missing-context"),
) -> None:
    store = _build_proposal_store(repo)
    try:
        updated = update_proposals(
            store,
            batch,
            proposal_ids,
            allowed_paths=allowed_paths or None,
            acceptance_criteria=acceptance_criteria or None,
            verification_commands=verification_commands or None,
            clear_missing_context=clear_missing_context,
        )
    except Exception as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    selected = set(proposal_ids)
    for proposal in updated.proposals:
        if proposal.proposal_id in selected:
            typer.echo(f"updated proposal {proposal.proposal_id}")


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
    issues: str | None = typer.Option(None, "--issues"),
    run_all: bool = typer.Option(False, "--all"),
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    if bool(issues) == bool(run_all):
        raise typer.BadParameter("specify exactly one of --issues or --all")

    loaded_config = load_config(config)
    repo_root = _resolve_repo_root(repo, loaded_config)
    issue_registry = build_issue_registry(repo_root)
    orchestrator = build_run_orchestrator(repo_root, loaded_config)

    try:
        if issues:
            selection = resolve_selected_issues(issue_registry, issues.split(","))
        else:
            selection = resolve_all_schedulable_issues(issue_registry)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    if not selection.items:
        typer.echo("no schedulable issues selected")
        raise typer.Exit(0)

    typer.echo(f"selected issues: {', '.join(selection.issue_ids)}")
    summary = run_batch(selection, orchestrator.run_one)
    typer.echo(summary.model_dump_json(indent=2, exclude_none=True))


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


@queue_app.command("add")
def queue_add(
    issue_ids: list[str] = typer.Argument(...),
    priority: str | None = typer.Option(None, "--priority"),
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = load_config(config)
    repo_root = _resolve_repo_root(repo, loaded_config)
    issue_registry = build_issue_registry(repo_root)

    try:
        result = admit_to_queue(issue_registry, issue_ids, priority=priority)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    for status in result.statuses:
        typer.echo(f"{status.issue_id} status={status.status} queue_priority={status.queue_priority}")
    typer.echo(
        f"requested={result.summary.requested} admitted={result.summary.admitted} already_admitted={result.summary.already_admitted}"
    )


@issue_app.command("ingest-github")
def issue_ingest_github(
    repo_full_name: str = typer.Option(..., "--repo-full-name"),
    issue: int = typer.Option(..., "--issue"),
    materialize_only: bool = typer.Option(False, "--materialize-only"),
    repo: Path | None = typer.Option(None, "--repo", exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    loaded_config = load_config(config)
    repo_root = _resolve_repo_root(repo, loaded_config)
    github_issue = fetch_github_issue(repo_full_name, issue)
    parsed = parse_github_issue_template(github_issue)

    provenance = check_issue_provenance(parsed, loaded_config)
    if not provenance.accepted:
        for reason in provenance.reasons:
            typer.echo(f"provenance rejected: {reason}", err=True)
        raise typer.Exit(1)

    admission = check_issue_admission(parsed, loaded_config)
    if not admission.accepted or admission.draft is None:
        for reason in admission.reasons:
            typer.echo(f"admission rejected: {reason}", err=True)
        raise typer.Exit(1)

    contract, record = materialize_issue(repo_root, admission.draft, loaded_config, queue_admitted=not materialize_only)
    typer.echo(
        f"ingested {contract.issue_id} from {repo_full_name}#{issue} "
        f"issue_state={record.issue_state} attempt_state={record.attempt_state}"
    )
