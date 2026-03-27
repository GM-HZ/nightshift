# Overnight Agent Loop Design V2

**Date:** 2026-03-26

**Status:** Supersedes the V1 design for implementation guidance while keeping V1 as historical context.

**Goal:** Define a practical, orchestrator-driven framework for running Codex or Claude Code overnight in a normal code repository using an autonomous `coding -> test -> fix -> commit` loop with branch isolation, worktree isolation, executable validation, bounded retries, structured state, and human review in the morning.

## 1. Why V2 Exists

V1 established the core workflow:

- issue-driven execution
- one issue, one branch
- tiered validation
- local structured state
- human merge gate

That version was directionally correct but too soft in several places that matter for unattended overnight execution:

- execution issues were not gated by executable validation
- validation contracts were not explicit enough for programmatic pass/fail decisions
- rollback and workspace recovery were underspecified
- orchestrator versus agent authority was not explicit enough
- long-run continuity still risked drifting toward chat-history dependence

V2 strengthens those areas and makes the system more operational.

## 2. Core Design Shift

The overnight system must not be modeled as one long-lived super-agent with one long-lived conversation.

It must be modeled as:

- a **long-lived orchestrator** that owns scheduling, validation, continuity, and authoritative state
- a set of **short-lived agents** that own local reasoning and local code edits only

In short:

- **Orchestrator owns continuity**
- **Agent owns issue-local execution**

This is the main architectural rule of V2.

## 3. Non-Negotiable Principles

1. **No executable validation, no execution issue**
   A task without programmatically checkable validation must not enter the overnight execution queue.

2. **Programmatic validation is the default judge**
   The agent may explain failures, but it must not act as the primary authority on whether an issue is solved.

3. **One execution issue, one branch, one isolated worktree**
   Isolation must protect both repository state and human work.

4. **Failed attempts must be cleanly reversible**
   Unverified changes must not leak into later attempts.

5. **Conversation context is ephemeral**
   Durable continuity must live in orchestrator-managed files, not in long-running chat history.

6. **The agent is disposable**
   Agents are workers, not the system of record.

7. **Human merge gate remains mandatory**
   The overnight system may branch and commit, but it must not merge autonomously.

## 4. Terminology

- **Backlog item:** A human-authored task in rough form, such as an item in `overnight_tasks.md`.
- **Normalized issue:** A task transformed into a structured unit with explicit scope, validation, and execution policy.
- **Execution issue:** A normalized issue small and concrete enough for overnight coding, with executable validation.
- **Planning issue:** A task too broad or underspecified for direct coding; it must be decomposed before execution.
- **Repro issue:** A task whose first objective is to create a deterministic reproducer or validation harness.
- **Investigation issue:** A task whose outcome is understanding or diagnosis, not an immediate code fix.
- **Run:** One overnight session governed by one orchestrator lifecycle.
- **Attempt:** One focused coding/test/fix cycle for one issue.
- **Tier 1 validation:** Issue-specific validation.
- **Tier 2 validation:** Core regression validation.
- **Tier 3 validation:** Full validation or broader promotion checks.

## 5. System Roles

### 5.1 Orchestrator Responsibilities

The orchestrator is the control plane of the overnight system. It owns:

- run lifecycle
- queue selection and priority
- worktree creation and cleanup
- branch creation and checkout
- pre-flight checks
- context packing
- validation execution or validation supervision
- retry and suspension decisions
- authoritative run state
- authoritative issue state
- morning summary generation

The orchestrator should be conservative, mechanical, and auditable.

### 5.2 Agent Responsibilities

The agent is a constrained execution worker. It owns:

- reading the current issue contract
- inspecting relevant code
- proposing one minimal attempt
- editing only allowed files
- explaining failures
- preparing structured attempt output
- preparing a commit message when validation succeeds

The agent does not own:

- queue management
- long-term memory
- pass/fail authority
- authoritative state persistence
- rollback policy
- merge decisions

## 6. Lifecycle Model

### 6.1 Run Lifecycle

One overnight run corresponds to one orchestrator lifecycle.

The orchestrator should:

- start with a run state file
- progress through multiple issues
- survive restarts by reloading local state
- end by writing a morning summary

### 6.2 Issue Lifecycle

An issue persists across attempts and can survive across multiple nights.

Suggested issue states:

- `draft`
- `ready`
- `running`
- `blocked`
- `done`
- `deferred`

Suggested issue subtypes:

- `execution`
- `planning`
- `repro`
- `investigation`

### 6.3 Agent Lifecycle

Agents must be short-lived.

Recommended V2 rule:

- create a fresh agent for each attempt

Minimum acceptable fallback:

- create a fresh agent for each issue

The preferred model is still **one attempt, one agent session**. This sharply reduces prompt drift, context pollution, and accumulated bad assumptions.

### 6.4 Context Lifecycle

- conversation context is temporary
- issue files and state files are durable
- run summaries are durable
- compressed historical summaries are durable

Continuity must be reconstructed from files, not inherited from an ever-growing chat transcript.

## 7. Context Architecture

Context must be explicitly layered.

### 7.1 Policy Context

Stable rules that rarely change:

- `program.md`
- `overnight/config.yaml`
- anti-cheating rules
- validation rules
- rollback rules
- output format rules

### 7.2 Issue Context

Only the current issue:

- issue contract
- goal
- acceptance
- allowed paths
- forbidden paths
- verification contract
- test edit permissions
- attempt limits
- recent blocker summaries
- branch and worktree metadata

### 7.3 Code Context

Only the local code needed for the current attempt:

- relevant source files
- relevant tests
- nearest call graph summary
- latest diff or failure location

### 7.4 Run Context

Held primarily by the orchestrator, injected only as compressed summaries when needed:

- remaining night budget
- number of attempts already used on this issue
- recent failure fingerprints
- current queue status
- high-level run scoreboard

### 7.5 Context Principle

The operating rule should be:

> The agent works in issue-scoped short context.
> Global continuity is maintained by orchestrator-managed local state.

## 8. Execution Issue Admission Rule

This rule must be explicit:

> No executable validation, no execution issue.

An execution issue must contain at least one programmatically checkable validation path, such as:

- issue-specific test command
- reproduction script
- deterministic acceptance command
- JSON-producing checker
- schema or output matcher

If that does not exist, the task must be downgraded to:

- `planning`
- `repro`
- `investigation`

## 9. Issue Model

Execution issues should be stored in YAML or JSON. Suggested V2 schema:

```yaml
id: 123
title: Fix cache invalidation race in session store
kind: execution
priority: high
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
  e2e_validation:
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
- `acceptance`
- `allowed_paths`
- `forbidden_paths`
- `verification`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`
- `risk`
- `status`

## 10. Verification Contract

V1 listed commands. V2 requires a contract.

Each validation block must define:

- whether it is required
- which commands run
- how pass is judged

Supported `pass_condition` types should include:

- `exit_code`
- `json_field_equals`
- `stdout_contains`
- `stderr_contains`
- `test_count_delta`
- `schema_match`

The default rule is:

- the orchestrator or a trusted checker evaluates pass/fail
- the agent may analyze failure output
- the agent may not self-certify success

## 11. Validation Tiers

### Tier 1: Issue Validation

Must directly verify the target issue.

### Tier 2: Regression Validation

Must protect critical repository behavior and must pass before progress is retained.

### Tier 3: Promotion Validation

Should be used for:

- nightly wrap-up
- branch promotion
- high-confidence candidate branches

Default V2 operating mode:

- Tier 1 required
- Tier 2 required
- Tier 3 optional

## 12. Branch and Worktree Strategy

### 12.1 Branch Naming

Each execution issue gets one branch:

```text
overnight/issue-<id>-<slug>
```

### 12.2 Worktree Isolation

Each execution issue should also get an isolated worktree.

Recommended structure:

```text
.overnight/worktrees/issue-123/
```

The human's main working tree must not be used as the overnight execution surface.

### 12.3 Why Worktrees Are Required

Worktree isolation protects against:

- accidental cleanup of a human's changes
- contamination between issue attempts
- branch-switch side effects
- dangerous global reset behavior

## 13. Attempt Size and Scope Control

V1 said "minimal attempt." V2 makes this enforceable.

### 13.1 Hard Scope Checks

The orchestrator must reject an attempt if it touches files outside `allowed_paths`.

### 13.2 Attempt Limits

The orchestrator should inspect attempt size using repository tooling such as:

- `git diff --stat`
- changed file count
- added/deleted line count

If an attempt exceeds configured thresholds:

- classify it as `scope_expansion_risk` or `attempt_rejected`
- either reject immediately or require explicit issue escalation logic

The thresholds are issue-configurable and should be conservative by default, but not so strict that ordinary bug fixes become impossible.

## 14. Pre-Flight Stage

Pre-flight is mandatory before code edits begin.

The orchestrator must check:

- worktree cleanliness
- branch and worktree correctness
- baseline Tier 1 and Tier 2 status when required
- required services or dependencies
- environment readiness

If baseline checks fail before editing, the issue must not proceed into coding.

Instead classify the blocker, such as:

- `infra_blocked`
- `dirty_baseline`
- `flaky_validation`

## 15. Attempt Execution Protocol

Each attempt should follow this sequence:

1. Select a `ready` execution issue.
2. Create or resume the issue branch and isolated worktree.
3. Run pre-flight checks.
4. Snapshot the pre-edit state.
5. Pack issue-scoped context.
6. Spawn a fresh short-lived agent.
7. Have the agent perform one minimal attempt.
8. Run orchestrator checks on changed scope.
9. Run Tier 1 validation.
10. If Tier 1 passes, run Tier 2 validation.
11. If validation passes, commit and record progress.
12. If validation fails, classify the failure and either retry or suspend.
13. Write authoritative state.
14. Rotate or continue according to budgets and progress rules.

## 16. Snapshot and Rollback Policy

Every attempt must begin with a recovery point.

Minimum required snapshot data:

- branch name
- worktree path
- `pre_edit_snapshot = git rev-parse HEAD`

If an attempt fails and should not be retained, rollback must be orchestrator-controlled.

Because V2 requires isolated worktrees, rollback can be strict within that worktree:

- restore tracked files to `pre_edit_snapshot`
- remove unapproved generated files in that worktree
- preserve only explicitly whitelisted artifacts

The system must not rely on the agent saying it has "cleaned up" the workspace.

## 17. Workspace Hygiene

The orchestrator must manage hygiene before and after attempts.

Checks should include:

- working tree clean or expected
- untracked file whitelist
- generated file whitelist
- temporary service cleanup
- lockfile or cache sanity where relevant

Long unattended runs accumulate debris. Hygiene is a first-class system responsibility.

## 18. Failure Taxonomy

Blocked is too coarse. V2 uses a blocker taxonomy.

Suggested blocker types:

- `infra_blocked`
- `dirty_baseline`
- `flaky_validation`
- `scope_expansion`
- `scope_expansion_risk`
- `forbidden_path_required`
- `needs_human_decision`
- `repeated_semantic_failure`
- `environment_misconfigured`

This makes morning review and next-night resumption much more efficient.

## 19. Failure Fingerprints

Retry budgets alone are not enough. The system must detect repeated ineffective attempts.

For each attempt, capture fingerprints such as:

- error fingerprint
- diff fingerprint
- tactic or hypothesis fingerprint

If multiple consecutive attempts are highly similar and produce no meaningful progress:

- classify as `repeated_semantic_failure`
- suspend the issue

## 20. Defining Progress

Progress must be explicit and mechanical where possible.

Suggested progress categories:

- `commit_worthy`
  - Tier 1 pass
  - Tier 2 pass
  - retained commit created

- `state_worthy`
  - deterministic reproducer established
  - failing-test count reduced but not yet fully passing
  - blocker sharply narrowed
  - new diagnostic knowledge captured structurally

- `no_progress`
  - equivalent failure repeated
  - no test improvement
  - no new information

This distinction matters for retry, suspension, and summary logic.

## 21. Retry and Budget Policy

Recommended defaults:

- maximum quick retries for a local mistake: `2`
- maximum failed attempts for one issue in one run: `5`
- maximum consecutive no-progress attempts: `3`
- per-command timeout: repository-specific and explicit
- per-issue per-night time budget: issue-configurable

If a single issue consumes its budget without `commit_worthy` progress, it must be rotated out.

## 22. Authoritative State Model

Local state remains the source of truth, but V2 clarifies ownership:

- the **agent** may emit a structured result proposal
- the **orchestrator** writes authoritative state after validating actual outcomes

Suggested mechanism:

- agent writes `attempt_result.json`
- orchestrator validates git state and validation outcomes
- orchestrator writes authoritative `issue_state.json`
- orchestrator updates `night-run.json`

The system must not trust the agent's self-reported success as authoritative state.

## 23. State Layout

Suggested directory structure:

```text
overnight/
  config.yaml
  core_regression.txt
  issues/
    123.yaml
    241.yaml
runs/
  2026-03-26/
    night-run.json
    summary.md
    run-summary.json
    issues/
      123.json
      241.json
.overnight/
  worktrees/
    issue-123/
    issue-241/
```

## 24. Run-Level State

Suggested `night-run.json` shape:

```json
{
  "run_date": "2026-03-26",
  "base_branch": "main",
  "started_at": "2026-03-26T22:00:00Z",
  "ended_at": null,
  "status": "running",
  "issues_attempted": [123, 241],
  "issues_completed": [],
  "issues_blocked": [123],
  "active_branches": ["overnight/issue-123-fix-cache-race"],
  "active_worktrees": [".overnight/worktrees/issue-123"],
  "commits_created": ["abc1234"]
}
```

## 25. Per-Issue State

Suggested `issue_state.json` shape:

```json
{
  "issue_id": 123,
  "branch": "overnight/issue-123-fix-cache-race",
  "worktree": ".overnight/worktrees/issue-123",
  "status": "blocked",
  "blocker_type": "repeated_semantic_failure",
  "attempts": [
    {
      "attempt": 1,
      "goal": "reproduce race with deterministic fixture",
      "files_touched": [
        "src/session/store.py",
        "tests/session/test_invalidation.py"
      ],
      "error_fingerprint": "nameerror-helper-fixture",
      "diff_fingerprint": "store-clear-cache-v1",
      "tactic_fingerprint": "clear-local-cache-on-invalidate",
      "tier1_passed": false,
      "tier2_passed": false,
      "progress": "state_worthy",
      "outcome": "retry",
      "error_summary": "NameError in helper fixture"
    }
  ],
  "latest_summary": "Blocked after repeated semantic failures; likely requires broader locking redesign."
}
```

## 26. Summary Compression

Long runs need compressed continuity.

V2 should keep:

- recent attempt details for the last few attempts
- compressed historical summaries for older attempts
- run-level scoreboard summaries

Prompt context should never include the full raw history by default.

## 27. Baseline Drift

The system should distinguish:

- issue-caused regression
- pre-existing baseline failure
- drift from the base branch

Suggested checks:

- record last known green baseline
- record validation fingerprints
- detect when the branch baseline changed independently of current issue work

Baseline drift should trigger diagnosis, not blind agent patching.

## 28. Base Branch Policy

The overnight system should use a stable base branch strategy.

Recommended V2 rule:

- all issue branches derive from a configured base branch or a nightly frozen baseline branch
- do not continuously rebase overnight issue branches onto a moving target

This reduces noise and makes morning review tractable.

## 29. Human-Facing Sync

External issue comments or PR drafts are for human visibility only.

Recommended sync content:

- branch name
- worktree path if useful locally
- latest commit
- current status
- blocker type
- short summary
- suggested next action

## 30. Morning Review Ordering

Morning review should be sorted, not just dumped.

Recommended review order:

1. small diff + Tier 1/Tier 2 passed
2. low-risk review-ready commits
3. blocked issues with clear human next steps
4. high-risk or cross-module branches
5. no-commit diagnostic outcomes with useful findings

## 31. Prompt Responsibilities

The agent prompt must encode operating discipline, not carry the whole system.

The prompt should make clear:

- you are working on one normalized execution issue
- you may only edit allowed files
- you must stay within attempt size limits
- you must not self-certify success
- you must not cheat by weakening tests without permission
- you must leave a concise structured attempt result

## 32. V2 Implementation Priorities

### P0

- execution issue admission rule
- verification contract
- programmatic validation authority
- isolated worktree strategy
- mandatory pre-flight
- snapshot and rollback
- orchestrator authoritative state
- issue-scoped context model

### P1

- failure fingerprints
- explicit progress taxonomy
- detailed test edit policy
- workspace hygiene
- blocker taxonomy

### P2

- summary compression
- baseline drift detection
- per-issue time budgets
- sorted morning review

## 33. Recommended Next Deliverables

The next implementation artifacts should be:

1. `overnight/config.yaml`
   Global policy for retries, timeouts, base branch, worktree layout, and validation defaults.

2. `overnight/issues/*.yaml`
   Normalized V2 issue definitions with verification contracts.

3. `overnight/program.md`
   Agent-facing execution protocol derived from this spec.

4. `scripts/run_overnight.py`
   Orchestrator that manages selection, worktrees, snapshots, validation, retries, rollback, and authoritative state.

5. `runs/<date>/summary.md`
   Sorted morning review output.

## 34. Decision Summary

V2 defines an overnight coding framework that is:

- orchestrator-driven rather than chat-driven
- issue-scoped rather than free-form
- validated by programs rather than agent self-judgment
- isolated by branch and worktree
- resilient through snapshots, rollback, and authoritative state
- durable through files rather than long conversation memory
- reviewable by humans in the morning

V1 remains useful as the first conceptual draft. V2 is the implementation-oriented design.
