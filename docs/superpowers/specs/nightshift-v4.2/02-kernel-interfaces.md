# 02. Kernel Interfaces

## Purpose

This document defines the stable kernel interfaces. These are interface boundaries, not implementation classes.

The goal is:

- keep the kernel small
- keep module seams explicit
- prevent product features from leaking into the execution core

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

## Issue Registry

### Responsibility

- store and load `IssueContract`
- store and load `IssueRecord`
- expose schedulable issues
- update issue-level lifecycle state

### Interface Shape

- `get_contract(issue_id) -> IssueContract`
- `get_record(issue_id) -> IssueRecord`
- `list_ready_issues() -> list[IssueRecord]`
- `update_issue_state(issue_id, issue_state, blocker_type=None, progress_type=None)`
- `attach_attempt(issue_id, attempt_id)`
- `attach_delivery(issue_id, delivery_state, delivery_ref=None)`

### Rules

- does not invoke engines
- does not run validation
- does not decide retries

## Run Orchestrator

### Responsibility

- own the overnight control loop
- choose next issue
- enforce budgets
- invoke workspace setup
- select engine
- drive validation
- decide retry, reject, defer, or block

### Interface Shape

- `start_run(config) -> RunState`
- `resume_run(run_id) -> RunState`
- `select_next_issue(run_state) -> issue_id | None`
- `execute_attempt(issue_id) -> attempt_id`
- `finalize_attempt(attempt_id)`
- `stop_run(run_id, reason)`

### Rules

- does not parse engine-native exceptions directly
- does not implement engine-specific logic
- uses normalized outcomes only

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

- persist current state snapshots
- append event history
- support crash recovery

### Interface Shape

- `save_run_state(run_state)`
- `save_issue_record(issue_record)`
- `save_attempt_record(attempt_record)`
- `append_event(event)`
- `load_run_state(run_id)`
- `load_issue_record(issue_id)`

### Rules

- no business decisions
- no engine invocation
- no hidden mutation side effects

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

## Interface Design Rule

The kernel should be written so that:

- adapters can be swapped
- state storage can be swapped
- notification transports can be swapped
- PR providers can be swapped

without rewriting the orchestrator core.
