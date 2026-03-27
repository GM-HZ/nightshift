# NightShift V4.2 Unified Spec

**Date:** 2026-03-27

**Status:** Unified product and kernel specification, further tightened after architectural review to harden state boundaries, engine contracts, and stable kernel module seams. Supersedes V4.1 as the primary design target while preserving V1, V2, and V3 as earlier design iterations.

**One-line definition:** NightShift is a harness for rolling overnight software delivery: humans prepare and approve automation-ready issues during the day, NightShift dispatches Codex CLI or Claude Code CLI to execute them overnight, independently validates outcomes, and hands review-ready branches or PRs to humans in the morning.

---

## 1. Purpose

This document unifies two perspectives that were previously split:

- the **PRD/product workflow** view from `nightshift.md`
- the **harness/kernel discipline** view from the V3 design

NightShift must satisfy both:

1. It must be easy to explain as a product workflow.
2. It must be strict enough internally to survive unattended overnight execution.

This document therefore separates:

- **Product Layer**: what NightShift is, how users experience it, and what the workflow looks like
- **Kernel Layer**: the execution constraints that keep the system safe, reviewable, and trustworthy

---

## 2. Product Vision

### 2.1 Slogan

Let software delivery roll like a night shift: humans split and approve work during the day, NightShift executes and validates all night, and humans review the results in the morning.

### 2.2 Product Positioning

NightShift is a lightweight workflow harness around strong AI coding engines.

It does **not** try to replace:

- Codex CLI
- Claude Code CLI
- repository CI
- human code review

It does provide:

- requirement-to-issue decomposition workflows
- automation readiness gating
- issue queue execution
- isolated coding workspaces
- independent verification
- retry and rejection handling
- PR or review handoff artifacts
- overnight run reporting

### 2.3 Product Boundary

NightShift is not:

- a general-purpose agent platform
- a multi-agent research system
- an autonomous merge bot
- a replacement for engineering management or product judgment

NightShift is:

- an AI coding harness
- for issue-sized work
- under human approval
- with strong post-execution verification

---

## 3. User Workflow

NightShift operates in three phases.

### 3.1 Phase A: Daytime Preparation

Humans are in the loop.

Workflow:

1. A human provides a large requirement, backlog area, or set of desired fixes.
2. NightShift helps decompose the work into issue-sized units.
3. A human reviews the proposed issue breakdown.
4. The human confirms, edits, removes, or adds issues.
5. Ready issues are normalized into execution-ready issue contracts.
6. The overnight queue is created.

### 3.2 Phase B: Overnight Execution

NightShift runs unattended.

Workflow:

1. Pick the next automation-ready issue.
2. Create an isolated branch and worktree.
3. Select an execution engine.
4. Dispatch the issue to Codex CLI or Claude Code CLI.
5. Run independent validation.
6. If valid, retain the result and prepare a PR or review artifact.
7. If invalid, reject, retry, or suspend according to policy.
8. Continue until the queue is exhausted, the run budget is spent, or safety limits trigger.

### 3.3 Phase C: Morning Review

Humans return as the final decision makers.

Workflow:

1. Review the overnight report.
2. Inspect accepted branches or PRs in ranked order.
3. Review blocked issues and handoff notes.
4. Merge, request follow-up, or discard.

---

## 4. Core Product Story

The intended story for a team is:

- During the day, people define and approve work units.
- At night, NightShift rolls through those issues one by one.
- Existing AI coding engines do the issue-local implementation work.
- NightShift independently verifies whether the work is acceptable.
- By morning, the team has a batch of reviewable outputs instead of a queue of untouched tasks.

This story is the product promise. The kernel rules below exist to make that promise credible.

---

## 5. Architecture Overview

NightShift has three layers.

### 5.1 Product Layer

User-facing workflow and operator experience:

- requirement splitting
- issue queue management
- run control
- report generation
- PR and review handoff

### 5.2 Harness Kernel Layer

Execution control and system safety:

- issue admission
- context packaging
- engine dispatch
- validation authority
- rollback and rejection
- workspace isolation
- authoritative state

### 5.3 Human Governance Layer

Humans retain authority over:

- whether work is ready for automation
- whether issue breakdown is correct
- whether accepted output should be merged
- whether ambiguous situations require product or architectural judgment

### 5.4 Stable Kernel Modules

V4.2 explicitly defines four stable kernel modules:

- **Issue Registry**
  Owns normalized issue contracts and issue-level lifecycle state.

- **Run Orchestrator**
  Owns queue selection, budgets, retries, rotation, and run-level control flow.

- **Engine Adapter Layer**
  Owns engine capability declarations, engine invocation, and normalized engine outcomes.

- **Validation Gate**
  Owns independent validation and acceptance or rejection decisions.

The following modules are intentionally outside the stable kernel and should remain replaceable edge modules:

- Requirement Splitter
- PR Dispatcher
- Report Generator
- Notification Adapter

This keeps the execution core small and stable while allowing the product surface to evolve more freely.

---

## 6. Fundamental System Rule

NightShift follows this rule:

> The harness governs. The engine executes. The human approves.

This rule resolves role confusion:

- Codex CLI and Claude Code CLI are execution engines
- NightShift is the control plane
- humans are the governance and merge gate

---

## 7. Kernel Principles

These are non-negotiable implementation rules.

1. **No executable validation, no execution issue**
   If a task cannot be programmatically checked, it cannot enter unattended coding.

2. **Execution engines are not the final judge**
   Engines may implement and self-report, but NightShift decides acceptance.

3. **One issue, one branch, one isolated worktree**
   Execution must be reviewable and safely discardable.

4. **Failed attempts must be easy to reject**
   Rejection, rollback, and rotation are normal behavior.

5. **Durable continuity lives in files, not chat history**
   Long-running operation must rely on state files, not a giant accumulated conversation.

6. **Humans approve automation entry and merge**
   NightShift can automate execution, not final governance.

---

## 8. Roles and Responsibilities

### 8.1 NightShift Harness

The harness owns:

- issue normalization
- readiness checks
- queue management
- branch and worktree setup
- context packaging
- engine invocation
- independent validation
- retry and suspension decisions
- authoritative run state
- authoritative issue state
- report generation
- PR or review handoff generation

### 8.2 Execution Engines

Execution engines include:

- Codex CLI
- Claude Code CLI

They own:

- issue-local code understanding
- issue-local coding
- local debugging within issue scope
- producing candidate changes
- producing structured execution output

They do not own:

- acceptance authority
- queue policy
- long-lived authoritative state
- merge decisions

### 8.3 Humans

Humans own:

- requirement intent
- issue decomposition approval
- deciding what is automation-ready
- merge or reject decisions
- product or architecture calls when ambiguity exists

---

## 9. Issue Taxonomy

NightShift supports multiple issue types, but only some are executable overnight.

### 9.1 Execution Issue

Ready for unattended coding.

Requirements:

- executable validation exists
- scope is bounded
- path constraints are explicit
- test permissions are explicit
- a human has approved automation

### 9.2 Planning Issue

Too large or unclear for direct execution.

Purpose:

- decompose into smaller issues

### 9.3 Repro Issue

Not yet ready for implementation because deterministic validation is missing.

Purpose:

- create a reproducer
- define executable acceptance
- then promote to execution issue

### 9.4 Investigation Issue

Diagnosis-only issue.

Purpose:

- produce structured findings
- explain blockers
- propose follow-up execution issues

---

## 10. Issue Admission Rule

This rule is mandatory:

> No executable validation, no execution issue.

Valid executable checks include:

- issue-specific test commands
- deterministic scripts
- machine-readable checkers
- JSON outputs with pass conditions
- output or schema matchers

Tasks lacking these checks must remain:

- planning
- repro
- investigation

They must not enter the unattended execution queue.

---

## 11. Issue Contract

The issue contract is the main input unit for the harness.

Suggested schema:

```yaml
id: 123
title: Fix cache invalidation race in session store
kind: execution
priority: high
engine_preferences:
  primary: codex
  fallback: claude_code
goal: Prevent stale session reads after invalidation under concurrent access.
description: >
  Existing invalidation logic allows stale reads under concurrent access.
acceptance:
  - deterministic invalidation test passes
  - core regression suite passes
allowed_paths:
  - src/session/
  - tests/session/
forbidden_paths:
  - migrations/
  - infra/
verification:
  issue_validation:
    required: true
    commands:
      - pytest tests/session/test_invalidation.py -q
    pass_condition:
      type: exit_code
      expected: 0
  static_validation:
    required: false
    commands:
      - ruff check src/session tests/session
      - mypy src/session
    pass_condition:
      type: all_exit_codes_zero
  regression_validation:
    required: true
    commands:
      - pytest tests/session/test_smoke.py -q
      - pytest tests/api/test_login.py -q
    pass_condition:
      type: exit_code
      expected: 0
  promotion_validation:
    required: false
    commands: []
    pass_condition: null
test_edit_policy:
  can_add_tests: true
  can_modify_existing_tests: true
  can_weaken_assertions: false
  requires_test_change_reason: true
attempt_limits:
  max_files_changed: 3
  max_lines_added: 80
  max_lines_deleted: 40
timeouts:
  command_seconds: 600
  issue_budget_seconds: 3600
risk: medium
status: ready
notes: Reproduce and fix only the invalidation race; do not redesign the storage backend.
last_attempt_summary: ""
```

### Required fields

- `id`
- `title`
- `kind`
- `priority`
- `goal`
- `allowed_paths`
- `forbidden_paths`
- `verification`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`
- `status`

### Product-facing fields

- `description`
- `acceptance`
- `notes`
- `risk`

### Kernel-facing fields

- `engine_preferences`
- `allowed_paths`
- `forbidden_paths`
- `verification`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`

---

## 12. Requirement Splitter

Requirement splitting belongs to the Product Layer.

### 12.1 Purpose

Help humans convert a large requirement into issue-sized work units.

### 12.2 Operation

1. Read basic repository context.
2. Call an AI engine to propose issue decomposition.
3. Present the proposed issues to the human.
4. Allow confirm, edit, delete, or add.
5. Save approved issues in normalized form.

### 12.3 Rules

The splitter must aim for issues that:

- can be implemented independently
- can be validated independently
- have small and clear scopes
- avoid cross-issue code dependency when possible

### 12.4 Governance Rule

AI may propose issue decomposition, but only human-approved issues enter the execution queue.

### 12.5 Repository Context Strategy

"Read basic repository context" is not an implementation detail. It is a first-class design concern because it drives both decomposition quality and token cost.

NightShift should acquire repository context in layers.

#### Layer 0: Cheap metadata

Always collect:

- top-level file tree summary
- primary language and framework signals
- build or package manifest files
- README and high-signal docs
- test directory distribution
- CI configuration summary if present

#### Layer 1: Relevant anchors

Collect based on requirement keywords and repository signals:

- likely target modules
- likely entrypoints
- nearby test files
- recent change hotspots if available

#### Layer 2: Focused deep reads

Use sparingly and only when decomposition quality requires it:

- specific implementation files
- local call chains
- schema or API definitions
- domain-specific design docs

#### Layer 3: Summarized carry-forward context

Persist compressed repository summaries so repeated decomposition runs do not need to reacquire the same expensive context from scratch.

#### Splitter Context Rule

The splitter must not indiscriminately read the whole repository. It must operate under explicit file-budget and token-budget constraints.

---

## 13. Queue Model

NightShift needs a queue of normalized issues.

V4.2 no longer treats all statuses as one flat field. The system must separate state domains.

### 13.1 IssueState

Describes whether the issue itself is eligible to be scheduled or resumed.

Suggested values:

- `draft`
- `ready`
- `running`
- `blocked`
- `deferred`
- `done`

### 13.2 AttemptState

Describes the most recent or current execution attempt on that issue.

Suggested values:

- `pending`
- `preflight_failed`
- `executing`
- `validating`
- `retryable`
- `accepted`
- `rejected`
- `aborted`

### 13.3 DeliveryState

Describes whether an accepted result has entered the review and merge surface.

Suggested values:

- `none`
- `branch_ready`
- `pr_opened`
- `reviewed`
- `merged`
- `closed_without_merge`

### 13.4 `blocked` vs `deferred`

These two statuses must remain semantically distinct.

- `blocked`
  The issue cannot continue under current conditions without an external change.
  Typical causes:
  - human decision required
  - forbidden path required
  - environment misconfigured
  - repeated semantic failure
  - missing dependency or credential

- `deferred`
  The issue is not permanently blocked, but the harness intentionally postpones it.
  Typical causes:
  - lower priority than other ready issues
  - insufficient remaining nightly budget
  - dependency expected to land later
  - promotion validation intentionally delayed
  - queue shaping or batching policy

Operational rule:

- `blocked` normally requires human or external intervention before resuming
- `deferred` may automatically re-enter the queue later without human action

### 13.5 State Composition Rule

Each issue record should store these state domains separately rather than collapsing them into a single overloaded `status`.

At minimum, the issue record should carry:

- `issue_state`
- `attempt_state`
- `delivery_state`
- `blocker_type`
- `progress_type`

Suggested queue-level operations:

- add issue
- inspect issue
- reprioritize issue
- mark blocked
- resume issue
- remove issue

The queue is part product workflow and part kernel control state.

---

## 14. Execution Lifecycle

For each execution issue:

1. Select next `ready` issue.
2. Create or resume isolated branch and worktree.
3. Run pre-flight checks.
4. Package execution context.
5. Dispatch selected engine.
6. Collect engine output.
7. Run independent validation.
8. Update `AttemptState` based on execution and validation outcomes.
9. Update `IssueState`, `DeliveryState`, `blocker_type`, and `progress_type` as needed.
10. Continue or rotate.

---

## 15. Context Packaging

NightShift should package context into four layers.

### 15.1 Policy Context

Stable rules:

- `program.md`
- NightShift config
- output schema
- anti-cheating rules
- validation rules

### 15.2 Issue Context

Current issue only:

- issue contract
- goal
- description
- acceptance
- path constraints
- test edit policy
- attempt limits
- branch and worktree metadata
- recent attempt summaries

### 15.3 Code Context

Only code relevant to the current issue:

- target source files
- target tests
- nearby failure locations
- prior accepted or rejected diffs if relevant

### 15.4 Run Context

Compressed harness-owned state:

- attempts used
- remaining budget
- recent failure fingerprints
- queue summary when needed

### 15.5 Context Rule

Execution engines must not depend on full-night chat history.

NightShift must preserve continuity through structured files.

---

## 16. Engine Adapter Model

NightShift should define a stable adapter interface for each execution engine.

Suggested logical interface:

- `prepare(issue_contract, workspace, context_bundle)`
- `execute()`
- `collect_result()`
- `normalize_output()`

### 16.1 Engine Capabilities Contract

The harness must know what an engine can do before dispatching work to it.

Suggested capability fields:

- `supports_streaming_output`
- `supports_structured_result`
- `supports_patch_artifact`
- `supports_resume`
- `supports_noninteractive_mode`
- `supports_worktree_execution`
- `supports_file_scope_constraints`
- `supports_timeout_enforcement`
- `supports_json_output_hint`

Capability declarations should be treated as part of the adapter contract, not hidden implementation detail.

### 16.2 Scheduling Rule

The harness should use engine capabilities when deciding:

- whether an engine is eligible for an issue
- whether fallback is possible
- whether a feature such as resume or structured output may be enabled

### 16.3 Engine Failure Contract

The adapter contract must define failure semantics, not only happy-path method names.

Every engine invocation should resolve into a normalized execution outcome rather than an unstructured exception boundary.

Suggested normalized outcomes:

- `success`
- `engine_timeout`
- `engine_crash`
- `partial_output`
- `invalid_output`
- `interrupted`
- `environment_error`

Each normalized result should include:

- engine name
- invocation id
- exit code if any
- start time
- end time
- duration
- stdout artifact path
- stderr artifact path
- raw transcript or log artifact paths if available
- recoverable flag
- engine error type
- summary message

### 16.4 Adapter Boundary Rule

Adapters may capture native engine exceptions, but they must normalize them before returning to the harness.

The harness should never need engine-specific exception parsing to decide whether to:

- retry
- fallback to another engine
- mark infra failure
- suspend the issue

Supported engines in V4:

- `codex`
- `claude_code`

Future engines may be added without changing the harness contract.

---

## 17. Validation Model

Validation is a kernel-owned acceptance gate.

### 17.1 Issue Validation

Directly verifies that the issue goal is satisfied.

### 17.2 Static Validation

Optional repository-specific checks:

- lint
- typecheck
- build

### 17.3 Regression Validation

Protects important existing behavior.

### 17.4 Promotion Validation

Optional broader checks for:

- PR readiness
- nightly wrap-up
- high-confidence branches

### 17.5 Default Policy

- issue validation required
- regression validation required
- static validation encouraged when cheap
- promotion validation optional

---

## 18. Validation Authority

NightShift must determine acceptance via programmatic checks such as:

- exit codes
- structured outputs
- test counts
- output matching
- schema checks

Execution engines may explain failures or interpret logs, but they must not be the primary acceptance judge.

### AI-as-Judge Limitation

If a product-facing scenario includes natural-language test cases or descriptions, AI analysis may be used as:

- helper feedback
- triage assistance
- issue refinement support

It must not be used as the main pass/fail gate for unattended acceptance.

This is a deliberate rejection of the looser AI-judged validation style.

---

## 19. Workspace Isolation

Each execution issue gets:

- one branch
- one isolated worktree

Recommended branch format:

```text
nightshift/issue-<id>-<slug>
```

Recommended worktree format:

```text
.nightshift/worktrees/issue-<id>/
```

The user's normal working tree must not be used for unattended execution.

---

## 20. Pre-Flight

Before engine dispatch, NightShift must verify:

- worktree cleanliness
- branch/worktree correctness
- environment readiness
- required services if applicable
- baseline validation health where relevant

If pre-flight fails, do not dispatch the engine.

Instead:

- classify the blocker
- update state
- rotate or stop according to policy

---

## 21. Attempt Limits

Attempt size must be checked by the harness.

Checks include:

- path scope
- file count
- line count
- forbidden path touches

If an attempt exceeds thresholds:

- reject it
- classify it as scope risk or scope expansion
- optionally re-dispatch with tighter instructions

---

## 22. Rejection and Rollback

Before each attempt, NightShift records:

- branch
- worktree
- pre-edit commit SHA

If an attempt is rejected:

- rollback is harness-controlled
- cleanup happens inside the isolated worktree
- only explicitly whitelisted artifacts are retained

Rejected attempts should not contaminate later attempts.

---

## 23. Retry Model

Retry exists to recover from cheap failures, not to rationalize endless looping.

Suggested policy:

- retry only when failure seems local and recoverable
- cap retries explicitly
- stop once repeated semantic failure is detected

Retry strategies may include:

- append failure output to context
- emphasize path constraints
- narrow scope to the most critical acceptance condition

But the harness must remain in control of retry policy and budgets.

---

## 24. Failure Taxonomy

Suggested blocker/failure types:

- `infra_blocked`
- `dirty_baseline`
- `flaky_validation`
- `scope_expansion`
- `scope_expansion_risk`
- `forbidden_path_required`
- `needs_human_decision`
- `repeated_semantic_failure`
- `environment_misconfigured`

Fine-grained blocker types make morning review and future optimization easier.

---

## 25. Failure Fingerprints

NightShift should detect repeated low-value attempts using:

- error fingerprint
- diff fingerprint
- tactic fingerprint

If repeated attempts are materially similar and produce no meaningful progress:

- stop retrying
- suspend the issue
- surface it for human handling

---

## 26. Progress Model

NightShift distinguishes:

### 26.1 Acceptance Progress

- required validation passes
- retained commit exists
- branch or PR is review-ready

### 26.2 Diagnostic Progress

- deterministic reproducer created
- blocker narrowed
- useful structured insight captured

### 26.3 No Progress

- repeated equivalent failure
- no test improvement
- no useful diagnostic gain

Only acceptance progress should normally retain code as a review candidate.

Diagnostic progress should retain state and notes, not necessarily code.

---

## 27. PR and Review Handoff

For accepted issues, NightShift should generate:

- branch name
- commit SHA list
- validation summary
- concise change summary
- retry history
- known risks
- suggested reviewer context
- PR draft body if integrated with a provider

NightShift may create a PR automatically, but merge must remain human-controlled.

Delivery transitions should happen through `DeliveryState`, not by mutating issue execution state.

---

## 28. Reporting

NightShift should generate a run report when:

- the queue is exhausted
- the total runtime budget is reached
- a stop command is issued
- a failure circuit breaker triggers

The report should include:

- run duration
- issue counts by outcome
- accepted issue list
- blocked issue list
- PR links if available
- retry and failure summaries
- detailed log locations

Morning review should present items in ranked order:

1. small validated diffs
2. low-risk accepted outputs
3. blocked issues with clear next steps
4. high-risk changes
5. diagnostic-only outputs

Reports are not a substitute for alerts. Reporting is for review and traceability, while alerting is for exceptional run-time situations that may require prompt awareness.

---

## 29. CLI Surface

NightShift should expose CLI commands in three groups.

### 29.1 Preparation

- `nightshift split --requirement '...' --repo /path/to/repo`
- `nightshift split --file requirement.md --repo /path/to/repo`

### 29.2 Queue and Execution

- `nightshift queue status`
- `nightshift queue show <id>`
- `nightshift run --repo /path/to/repo`
- `nightshift run --repo /path/to/repo --daemon`
- `nightshift run-one <id> --repo /path/to/repo`
- `nightshift status`
- `nightshift stop`

### 29.3 Reports

- `nightshift report`
- `nightshift report --run <run-id>`

---

## 30. Configuration

Each repository should define a config file such as `nightshift.yaml`.

Suggested areas:

- `project`
  - repo path
  - main branch

- `runner`
  - default engine
  - engine fallback
  - issue timeout
  - total overnight timeout

- `validation`
  - lint command
  - typecheck command
  - build command
  - core regression commands

- `retry`
  - max retries
  - failure circuit breaker
  - retry strategy defaults

- `pr`
  - labels
  - reviewers
  - provider integration

- `report`
  - output directory
  - notification settings

### 30.1 Alerting Semantics

`notification_settings` must correspond to explicit event semantics rather than being a passive transport field.

Suggested critical alert events:

- run aborted unexpectedly
- global timeout reached
- circuit breaker triggered
- environment failure prevents queue progress
- state store corruption or recovery failure
- repeated engine crashes across multiple issues

Suggested warning-level events:

- issue blocked
- repeated retry exhaustion on one issue
- engine fallback activated
- flaky validation pattern detected

Operational rule:

- critical alerts should notify promptly
- warning alerts may be batched or summarized depending on user preferences

---

## 31. State Ownership

NightShift is the source of truth for run state and issue state.

Execution engines may emit:

- execution summary
- changed files
- self-reported outcome
- proposed commit message

NightShift writes:

- authoritative attempt result
- issue state
- run state
- acceptance or rejection record

This keeps the kernel reliable even when engine output varies.

### 31.1 Current State vs Event Log

V4.2 distinguishes between:

- **current state snapshots**
  Used by the harness for live decision-making

- **append-only event history**
  Used for auditability, replay, debugging, and future analytics

MVP may still optimize around current-state files, but the design should leave room for append-only event capture.

---

## 32. State Layout

Suggested structure:

```text
nightshift/
  config.yaml
  issues/
    123.yaml
    241.yaml
  engines/
    codex.md
    claude_code.md
nightshift-data/
  runs/
    2026-03-27/
      run-state.json
      events.ndjson
      report.md
      issues/
        123.json
        241.json
.nightshift/
  worktrees/
    issue-123/
    issue-241/
```

---

## 33. MVP Scope

V4 intentionally narrows MVP.

### Must-have

- issue contract schema
- split state model for issue, attempt, and delivery
- queue and run control
- engine adapter for Codex CLI
- engine adapter for Claude Code CLI
- engine capability registry
- isolated branch/worktree management
- independent validation gate
- rejection and rollback
- reporting

### Nice-to-have but not required for MVP

- remote issue sync
- remote PR sync
- dashboards
- dependency-aware scheduling
- parallel execution

This is a correction to earlier designs that tried to do too much in the first release.

---

## 34. Success Metrics

Suggested first metrics:

- first-attempt issue success rate
- eventual issue success rate within retry budget
- mean time per issue
- number of review-ready outputs per night
- human review acceptance rate
- human intervention rate

These metrics should be used for iteration, not vanity.

---

## 35. V4.2 Summary

NightShift V4.2 unifies:

- the product workflow from the PRD view
- the execution discipline from the harness/kernel view

Its defining characteristics are:

- human-approved issue preparation during the day
- overnight execution by Codex CLI or Claude Code CLI
- harness-owned independent validation
- branch and worktree isolation
- rejection and rollback as first-class behavior
- morning review and human-controlled merge

Compared with V4.1, V4.2 additionally hardens three core architectural seams:

- split state domains for issue, attempt, and delivery
- explicit engine capability contracts alongside normalized outcomes
- a smaller, more stable kernel module boundary

This is the most practical design so far because it is both:

- understandable as a product
- defensible as an engineering system
