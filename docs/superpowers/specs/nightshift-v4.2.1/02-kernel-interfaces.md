# 02. Kernel Interfaces

## Purpose

This document defines the V4.2.1 stable kernel interfaces.

The V4.2.1 revision mainly closes interface gaps around:

- current issue record ownership
- queue runtime mutations
- run recovery
- reporting and audit reads

These are interface boundaries, not implementation classes.

## Stable Kernel Modules

The stable kernel consists of:

- Issue Registry
- Run Orchestrator
- Engine Adapter Layer
- Validation Gate

Supporting infrastructure interfaces are still required:

- Workspace Manager
- State Store

Edge modules remain outside the stable kernel:

- Requirement Splitter
- PR Dispatcher
- Report Generator
- Notification Adapter

## Ownership Rule

V4.2.1 makes ownership explicit:

- `Issue Registry`
  Owns immutable `IssueContract` objects and current mutable `IssueRecord` objects
- `State Store`
  Owns `RunState`, `AttemptRecord`, append-only event history, and alert history

The Orchestrator must use these module interfaces rather than directly reading or mutating persistence files.

## Issue Registry

### Responsibility

- store and load `IssueContract`
- store and load current `IssueRecord`
- expose schedulable issues
- expose queue metadata such as `queue_priority`
- update issue-level lifecycle state

### Interface Shape

- `save_contract(issue_contract) -> None`
- `get_contract(issue_id) -> IssueContract`
- `list_contracts(kind=None) -> list[IssueContract]`
- `get_record(issue_id) -> IssueRecord`
- `save_record(issue_record) -> None`
- `list_schedulable_records() -> list[IssueRecord]`
- `set_queue_priority(issue_id, queue_priority) -> IssueRecord`
- `attach_attempt(issue_id, attempt_id, attempt_state, run_id) -> IssueRecord`
- `attach_delivery(issue_id, delivery_state, delivery_id=None, delivery_ref=None) -> IssueRecord`

### Rules

- does not invoke engines
- does not run validation
- does not decide retries
- is the source-of-truth interface for current mutable issue state

## Run Orchestrator

### Responsibility

- own the overnight control loop
- choose next issue
- enforce budgets
- invoke workspace setup
- select engine
- drive validation
- decide retry, reject, defer, or block
- coordinate recovery against prior run state

### Interface Shape

- `start_run(config) -> RunState`
- `recover_run(source_run_id) -> RunState`
- `select_next_issue(run_state) -> issue_id | None`
- `execute_attempt(issue_id) -> attempt_id`
- `finalize_attempt(attempt_id)`
- `stop_run(run_id, reason)`

### Rules

- does not parse engine-native exceptions directly
- does not implement engine-specific logic
- uses normalized outcomes only
- does not patch persistence files directly
- recovery from an interrupted source run returns a new controlling `RunState` with a new `run_id`

## Engine Adapter

### Responsibility

- declare engine capabilities
- package engine invocation
- execute CLI
- return normalized `EngineOutcome`

### Interface Shape

- `name() -> str`
- `capabilities() -> EngineCapabilities`
- `prepare(issue_contract, workspace, context_bundle) -> PreparedInvocation`
- `execute(prepared_invocation) -> EngineOutcome`
- `normalize_output(raw_result) -> EngineOutcome`

### Rules

- no acceptance authority
- no mutation of issue registry
- no direct notification side effects

## Validation Gate

### Responsibility

- run independent verification
- evaluate pass conditions
- emit `ValidationResult`
- advise acceptance or rejection

### Interface Shape

- `validate(issue_contract, workspace, attempt_record) -> ValidationResult`
- `evaluate_acceptance(validation_result) -> bool`

### Rules

- does not care which engine produced the code
- does not own retry policy
- does not mutate delivery state

## Workspace Manager

### Responsibility

- create and clean worktrees
- manage branches
- record pre-edit snapshot
- perform rollback

### Interface Shape

- `prepare_workspace(issue_contract) -> WorkspaceHandle`
- `snapshot(workspace) -> SnapshotHandle`
- `rollback(workspace, snapshot)`
- `cleanup(workspace)`

### Rules

- no validation logic
- no engine selection logic

## State Store

### Responsibility

- persist run-scoped current state snapshots
- persist attempt history
- append and read event history
- append and read alert history
- support crash recovery and report reads

### Interface Shape

- `save_run_state(run_state) -> None`
- `load_run_state(run_id) -> RunState`
- `list_runs(limit=None) -> list[RunState]`
- `set_active_run(run_id_or_none) -> None`
- `get_active_run() -> str | None`
- `save_run_issue_snapshot(run_id, issue_record) -> None`
- `list_run_issue_snapshots(run_id) -> list[IssueRecord]`
- `save_attempt_record(attempt_record) -> None`
- `load_attempt_record(attempt_id) -> AttemptRecord`
- `list_attempt_records(run_id, issue_id=None) -> list[AttemptRecord]`
- `append_event(event_record) -> None`
- `read_events(run_id, issue_id=None, since_seq=None) -> list[EventRecord]`
- `append_alert(alert_event) -> None`
- `read_alerts(run_id=None, issue_id=None, severity=None) -> list[AlertEvent]`

### Rules

- no business decisions
- no engine invocation
- no hidden mutation side effects
- not the authoritative write interface for current `IssueRecord`

## Dependency Rules

Allowed dependencies:

- Orchestrator -> Issue Registry
- Orchestrator -> Workspace Manager
- Orchestrator -> Engine Adapter
- Orchestrator -> Validation Gate
- Orchestrator -> State Store
- Orchestrator -> Notification Adapter
- Report Generator -> State Store
- PR Dispatcher -> Issue Registry, State Store

Forbidden or discouraged dependencies:

- Validation Gate -> Engine Adapter
- Engine Adapter -> Issue Registry
- Requirement Splitter -> Validation Gate internals
- Notification Adapter -> Orchestrator internals

## Interface Sufficiency Rule

The kernel should be written so that:

- adapters can be swapped
- state storage can be swapped
- notification transports can be swapped
- PR providers can be swapped

without rewriting the orchestrator core.

That goal only holds if the interfaces above are sufficient for:

- queue inspection
- queue reprioritization
- recovery after interruption
- attempt inspection
- historical run report generation from targeted run snapshots
- run reporting
- audit replay
