# Overnight Coding Harness Design V3

**Date:** 2026-03-27

**Status:** Supersedes V2 as the implementation target while keeping V1 and V2 as historical design steps.

**Goal:** Define a harness-centric framework for running Codex CLI and Claude Code CLI overnight in normal repositories, using them as interchangeable execution engines for issue-scoped implementation while the harness owns task admission, isolation, validation, rejection, state, and human review handoff.

## 1. Why V3 Exists

V1 and V2 assumed the system itself would own more of the agent runtime model:

- V1 established the basic overnight loop.
- V2 clarified orchestrator authority, validation contracts, rollback, and context boundaries.

After further reflection, the more practical framing is:

- single-issue coding already has strong off-the-shelf engines
- Codex CLI and Claude Code CLI are the execution core
- the real product opportunity is the **harness** around them

V3 therefore shifts the system boundary:

- **The harness is the product**
- **Codex CLI / Claude Code CLI are execution engines**
- **Humans remain the approval and merge authority**

## 2. Core Architecture

V3 has three layers:

1. **Harness**
   The control plane that manages issue readiness, execution, validation, rejection, retry, state, and review handoff.

2. **Execution Engine**
   A pluggable CLI executor such as Codex CLI or Claude Code CLI that performs issue-scoped coding work.

3. **Human Review Layer**
   Humans decide issue readiness, inspect results, approve PRs, and merge.

The critical rule is:

> The harness governs. The engine executes. The human approves.

## 3. Scope of the Harness

The harness is responsible for:

- converting rough work into executable issue contracts
- deciding whether an issue is eligible for automation
- assigning a branch and isolated worktree
- packaging execution context
- invoking Codex CLI or Claude Code CLI
- running independent validation after engine execution
- accepting or rejecting candidate results
- tracking retries, blockers, and outcomes
- generating review-ready output for humans

The harness is not responsible for:

- reimplementing the coding intelligence of Codex or Claude Code
- replacing repository CI
- autonomously merging into the base branch

## 4. Design Principles

1. **Execution engine, not homegrown agent core**
   The harness should wrap strong existing coding CLIs instead of trying to recreate them.

2. **No executable validation, no executable issue**
   A task must have programmatic validation before it is allowed into the automated loop.

3. **One issue, one branch, one isolated worktree**
   Each execution unit must remain reviewable and safely discardable.

4. **Engine is not the final judge**
   The harness and independent validation determine acceptance or rejection.

5. **Humans approve issue creation and merge**
   The system may automate execution, not governance.

6. **Execution is issue-scoped**
   The engine should receive only the policy, issue, and local code context needed for one issue.

7. **Failure must be cheap**
   Rejection, rollback, and rotation must be normal system behavior.

## 5. Mental Model

The product is best understood as:

- a task decomposition and execution harness
- for AI coding engines
- operating on issue-sized work
- under repository-specific policy

This is not "one autonomous agent running all night."

It is:

- a harness repeatedly dispatching issue-sized jobs
- to a trusted coding engine
- and independently checking the results

## 6. End-to-End Workflow

The intended loop is:

1. A large problem is broken into issue-sized tasks.
2. A human confirms which tasks are automation-ready.
3. The harness creates an issue contract.
4. The harness prepares an isolated branch and worktree.
5. The harness selects an execution engine.
6. The engine performs issue-scoped coding and local fix attempts.
7. The harness runs independent validation.
8. If validation passes, the harness keeps the result and prepares a PR or review artifact.
9. If validation fails, the harness rejects, rolls back, retries, or suspends the issue.
10. A human reviews and decides whether to merge.

## 7. Issue Taxonomy

V3 keeps the issue taxonomy but reframes it around harness readiness.

### 7.1 Execution Issue

Suitable for automated coding now.

Requirements:

- executable validation exists
- scope is bounded
- allowed paths are known
- test and verification rules are clear
- human has approved automation on this issue

### 7.2 Planning Issue

Too broad or underspecified for direct execution.

Typical next action:

- decompose into smaller issues

### 7.3 Repro Issue

The immediate goal is to create a deterministic reproducer or acceptance check.

Typical next action:

- convert into execution issue after validation is established

### 7.4 Investigation Issue

The goal is diagnosis, not code retention.

Typical output:

- structured findings
- blocker explanation
- recommended follow-up issue breakdown

## 8. Issue Admission Rule

This rule remains mandatory:

> No executable validation, no execution issue.

An execution issue must include at least one harness-checkable validation path such as:

- issue-specific test command
- reproduction script
- deterministic checker
- machine-readable JSON result
- schema or output matcher

If a task lacks this, it must stay outside the execution queue until a human or a repro flow upgrades it.

## 9. Issue Contract

The issue contract is the harness input unit.

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

### Optional but useful fields

- `engine_preferences`
- `risk`
- `notes`
- `last_attempt_summary`

## 10. Harness Responsibilities in Detail

### 10.1 Intake and Normalization

The harness should support rough input sources such as:

- `overnight_tasks.md`
- local issue files
- remote issue trackers

But it should execute only normalized issue contracts.

### 10.2 Readiness Gate

Before queueing an issue, the harness must verify:

- executable validation exists
- scope is bounded
- test permissions are explicit
- path constraints are explicit
- a human has approved automation on this issue

### 10.3 Workspace Management

The harness must own:

- branch creation
- isolated worktree creation
- snapshotting
- rollback
- cleanup

### 10.4 Execution Dispatch

The harness must:

- choose the configured engine
- package the issue-scoped context
- invoke the engine CLI
- collect structured execution artifacts

### 10.5 Independent Validation

The harness must run or supervise post-execution validation that is independent of engine self-reporting.

### 10.6 Acceptance Decision

The harness must decide:

- keep
- reject
- retry
- suspend
- escalate to human

### 10.7 Review Handoff

For accepted results, the harness should produce:

- branch name
- commit list
- validation summary
- risk notes
- PR draft or review summary

## 11. Execution Engine Responsibilities

The execution engine is the coding worker for one issue.

It should:

- read the issue prompt package
- inspect relevant repository code
- perform issue-scoped coding
- locally iterate on failing tests when helpful
- emit a structured execution result

It should not:

- decide final acceptance
- bypass harness constraints
- write authoritative run state
- merge

## 12. Engine Adapter Model

V3 should define a stable executor interface so multiple CLIs can be swapped in.

Suggested logical interface:

- `prepare(issue_contract, workspace, context_bundle)`
- `execute()`
- `collect_result()`
- `normalize_output()`

Supported engines in V3:

- `codex`
- `claude_code`

Future engines may be added without changing the core harness contract.

## 13. Human Review Layer

Humans remain responsible for:

- decomposing large problems
- approving which issues enter automation
- reviewing accepted branches or PRs
- deciding whether to merge
- resolving ambiguous product or architecture choices

Humans are not expected to babysit each coding attempt, but they remain the governance layer.

## 14. Context Packaging

The harness should package context into four layers.

### 14.1 Policy Context

Stable rules:

- `program.md`
- harness config
- anti-cheating rules
- validation rules
- output schema

### 14.2 Issue Context

Current issue only:

- issue contract
- acceptance
- path constraints
- verification contract
- test edit policy
- attempt limits
- branch and worktree metadata
- recent attempt summaries

### 14.3 Code Context

Only the code relevant to the issue:

- relevant source files
- relevant tests
- nearest failure location
- recent accepted or rejected diffs if useful

### 14.4 Run Context

Compressed harness-owned state:

- attempts already used
- recent failure fingerprints
- remaining budget
- queue summary if necessary

The engine should not depend on full-night conversation history.

## 15. Lifecycle Model

### 15.1 Harness Lifecycle

The harness is long-lived across the overnight run.

It owns:

- queue state
- issue state
- workspace state
- validation history
- morning summary

### 15.2 Engine Lifecycle

The engine should be short-lived and issue-scoped.

Preferred rule:

- one engine invocation per attempt

Minimum fallback:

- one engine invocation per issue

The harness should prefer fresh invocations to reduce drift and contamination.

### 15.3 Issue Lifecycle

Suggested statuses:

- `draft`
- `ready`
- `running`
- `blocked`
- `done`
- `deferred`

### 15.4 Attempt Lifecycle

Each attempt is:

- prepared by the harness
- executed by the engine
- judged by the harness
- recorded by the harness

## 16. Validation Model

Validation remains tiered, but V3 frames it as a harness gate.

### Tier 1: Issue Validation

Directly proves the target issue is addressed.

### Tier 2: Core Regression Validation

Protects important existing system behavior.

### Tier 3: Promotion Validation

Used for:

- PR readiness
- nightly wrap-up
- high-confidence candidate branches

Default mode:

- Tier 1 required
- Tier 2 required
- Tier 3 optional

## 17. Programmatic Pass/Fail Authority

The engine may report:

- what it changed
- what it believes happened
- why it thinks a fix works

But the harness must determine acceptance using:

- exit codes
- structured command outputs
- test counts
- output matching
- schema checks

This prevents the engine from being both implementer and judge.

## 18. Branch and Worktree Policy

Each execution issue gets:

- one dedicated branch
- one dedicated isolated worktree

Recommended branch naming:

```text
overnight/issue-<id>-<slug>
```

Recommended worktree layout:

```text
.overnight/worktrees/issue-<id>/
```

The user's main working tree must never be the overnight execution surface.

## 19. Pre-Flight

Before engine execution, the harness must check:

- worktree cleanliness
- branch/worktree correctness
- environment readiness
- service availability if required
- baseline validation health where applicable

If pre-flight fails, do not dispatch the engine.

Instead classify the issue as blocked with a specific blocker type.

## 20. Attempt Limits

Attempt size must be enforced by the harness, not just suggested to the engine.

Checks should include:

- touched paths
- file count
- line count
- forbidden path access

The harness may:

- reject oversized attempts
- classify them as `scope_expansion_risk`
- require issue escalation

## 21. Snapshot, Rejection, and Rollback

Before each attempt, the harness must record:

- branch
- worktree
- pre-edit commit SHA

If an attempt is rejected, rollback must be harness-controlled.

Because execution happens in isolated worktrees, rollback can be strict there without threatening the user's main workspace.

## 22. Acceptance Outcomes

For each attempt, the harness should classify one of:

- `accepted`
- `rejected`
- `retry`
- `blocked`
- `needs_human_decision`

### Accepted

- required validation passes
- branch state is consistent
- result is retained

### Rejected

- validation fails
- no useful progress justifies retention
- workspace is rolled back

### Retry

- failure appears local and recoverable
- retry budget remains

### Blocked

- issue cannot proceed under current constraints

### Needs Human Decision

- product or architecture ambiguity
- forbidden path would be required
- test policy conflict

## 23. Failure Taxonomy

Suggested blocker and failure labels:

- `infra_blocked`
- `dirty_baseline`
- `flaky_validation`
- `scope_expansion`
- `scope_expansion_risk`
- `forbidden_path_required`
- `needs_human_decision`
- `repeated_semantic_failure`
- `environment_misconfigured`

## 24. Failure Fingerprints

The harness should track repeated low-value attempts using:

- error fingerprint
- diff fingerprint
- tactic fingerprint

If similar attempts repeat without meaningful progress, the harness should suspend rather than keep paying engine cost.

## 25. Progress Model

V3 distinguishes:

- `acceptance_progress`
  - validation passes
  - commit retained
  - PR-ready or review-ready output produced

- `diagnostic_progress`
  - deterministic repro created
  - blocker narrowed
  - useful structured insight captured

- `no_progress`
  - repeated equivalent failure
  - no test improvement
  - no new knowledge

Only `acceptance_progress` should normally retain code changes.

`diagnostic_progress` should retain structured state and summaries, not necessarily code.

## 26. State Ownership

The harness is the source of truth.

The engine may emit:

- execution summary
- changed files
- proposed commit message
- self-reported outcome

The harness writes:

- authoritative attempt result
- issue state
- run state
- acceptance/rejection record

## 27. Local State Layout

Suggested structure:

```text
overnight/
  config.yaml
  issues/
    123.yaml
    241.yaml
  engines/
    codex.md
    claude_code.md
runs/
  2026-03-27/
    run-state.json
    summary.md
    issues/
      123.json
      241.json
.overnight/
  worktrees/
    issue-123/
    issue-241/
```

## 28. Review Handoff

For each accepted issue, the harness should generate:

- branch name
- commit SHA list
- validation results
- concise change summary
- known risks
- suggested review order
- PR draft body if desired

Morning review should be sorted by:

1. small validated diffs
2. low-risk high-confidence fixes
3. blocked issues with clear next steps
4. high-risk changes
5. diagnostic-only outputs

## 29. V3 Product Boundary

The harness should stop at:

- issue creation and normalization
- execution dispatch
- validation and rejection
- review handoff

The harness should not own:

- merge automation by default
- replacing CI
- replacing the coding engine itself

## 30. Implementation Priorities

### P0

- issue contract schema
- execution engine adapter interface
- isolated branch/worktree manager
- independent validation gate
- rejection and rollback logic
- harness-owned authoritative state
- review handoff artifact generation

### P1

- engine selection policy
- failure fingerprinting
- progress taxonomy
- remote issue/PR synchronization
- sorted morning review

### P2

- automatic backlog-to-issue conversion
- branch promotion flows
- multi-engine comparison
- analytics dashboard

## 31. Recommended Next Deliverables

The next artifacts should be:

1. `overnight/config.yaml`
   Harness policy, retries, timeouts, branch/worktree rules, engine defaults.

2. `overnight/issues/*.yaml`
   Issue contracts.

3. `overnight/program.md`
   Engine-facing execution rules.

4. `scripts/run_overnight.py`
   Main harness runner.

5. `overnight/engines/codex.md`
   Adapter prompt contract for Codex CLI.

6. `overnight/engines/claude_code.md`
   Adapter prompt contract for Claude Code CLI.

7. `runs/<date>/summary.md`
   Morning review output.

## 32. Decision Summary

V3 reframes the overnight system as a **coding harness** rather than a self-contained agent platform.

The harness:

- governs issue readiness
- isolates execution
- dispatches Codex CLI or Claude Code CLI
- independently validates results
- rejects bad outcomes
- keeps accepted outcomes reviewable
- hands final merge authority to humans

This is the most practical version so far because it builds around strong existing engines instead of competing with them.
