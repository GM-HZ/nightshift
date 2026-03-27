# Overnight Agent Loop Design

**Date:** 2026-03-26

**Goal:** Define a practical framework for running Codex or Claude Code overnight in a normal code repository using an autonomous `coding -> test -> fix -> commit` loop with branch isolation, issue tracking, bounded retries, and human review in the morning.

## 1. Problem Statement

The target workflow is:

- Humans describe work as backlog items or issues.
- An agent picks one executable issue at a time.
- The agent creates a dedicated branch, makes a small change, runs tests, fixes failures, and commits only verified progress.
- The agent records structured progress locally and mirrors a readable status back to the issue system.
- The agent never auto-merges. A human reviews and integrates the results later.

The design goal is not maximum autonomy. The design goal is stable overnight throughput without damaging the repository or wasting the night on repeated failures.

## 2. Design Principles

1. **Issue-driven execution**
   The agent must consume a normalized issue, not free-form backlog text.

2. **One issue, one branch**
   Each execution issue has a dedicated local branch. No branch may mix multiple issues.

3. **Small-step progress**
   Each loop iteration should aim at one specific, verifiable improvement.

4. **Verification before retention**
   A change is only kept if the required verification passes.

5. **Bounded retries**
   The agent may attempt local fixes, but repeated failure must cause suspension and queue rotation.

6. **Local structured state is the source of truth**
   External issue comments are for human visibility. Local machine-readable logs drive agent continuity.

7. **Human merge gate**
   The agent may branch and commit, but it must not merge by itself.

## 3. Terminology

- **Backlog item:** A human-authored task in rough form, such as an item in `overnight_tasks.md`.
- **Normalized issue:** A task transformed into a structured unit with explicit validation and scope.
- **Execution issue:** A normalized issue small and clear enough for overnight coding.
- **Planning issue:** A task too large or unclear for direct overnight execution; it requires decomposition first.
- **Run:** One overnight session.
- **Attempt:** One focused coding/test/fix cycle within a single issue branch.
- **Core regression suite:** A small, predefined set of important regression checks that must pass in addition to issue-specific tests.

## 4. System Overview

The framework consists of six layers:

1. **Task source**
   Human-maintained backlog or issue list.

2. **Issue normalizer**
   Converts rough tasks into normalized issues with explicit fields.

3. **Queue manager**
   Selects only execution issues for overnight work and prioritizes them.

4. **Execution engine**
   Runs the branch-isolated coding/test/fix loop.

5. **State store**
   Saves structured local state for resumability and analysis.

6. **Review handoff**
   Produces a morning-ready summary with branches, commits, outcomes, and blockers.

## 5. Recommended Workflow

### 5.1 Before the night

Humans or a preparation script should:

- Gather candidate backlog items.
- Normalize them into structured issues.
- Mark each issue as either `execution` or `planning`.
- Assign priority.
- Define test commands.
- Define allowed and forbidden paths.
- Define whether tests may be edited.

### 5.2 During the night

The agent should:

1. Pick the highest-priority execution issue that is not blocked or exhausted.
2. Create or resume the issue branch.
3. Read the issue contract and recent state.
4. Perform one small coding attempt.
5. Run required validation.
6. Keep and commit only verified improvements.
7. Retry within limits if the failure looks local and recoverable.
8. Suspend the issue if it stops making progress.
9. Move on to the next execution issue.

### 5.3 In the morning

A human should receive:

- A run summary.
- A list of active issue branches.
- A list of commits made.
- A list of blocked issues and reasons.
- A recommended review order.

## 6. Issue Model

Every execution issue should be represented in a machine-readable format. JSON or YAML both work. Suggested fields:

```yaml
id: 123
title: Fix cache invalidation race in session store
kind: execution
priority: high
goal: Prevent stale session reads after invalidation under concurrent access.
acceptance:
  - tests/session/test_invalidation.py passes
  - core regression suite passes
allowed_paths:
  - src/session/
  - tests/session/
forbidden_paths:
  - migrations/
  - infra/
issue_test_commands:
  - pytest tests/session/test_invalidation.py -q
core_regression_commands:
  - pytest tests/session/test_smoke.py -q
  - pytest tests/api/test_login.py -q
can_edit_tests: true
risk: medium
notes: Reproduce and fix only the invalidation race; do not redesign the storage backend.
status: ready
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
- `issue_test_commands`
- `core_regression_commands`
- `can_edit_tests`
- `risk`
- `status`

### Status values

- `draft`
- `ready`
- `running`
- `blocked`
- `done`
- `deferred`

## 7. Branch and Commit Strategy

### Branch naming

Each execution issue gets its own branch:

```text
overnight/issue-<id>-<slug>
```

Examples:

- `overnight/issue-123-fix-cache-race`
- `overnight/issue-241-add-null-guard`

### Rules

- One issue must map to one branch.
- One branch must not carry work for multiple issues.
- The branch may contain multiple commits if the issue makes verified progress over time.
- The branch must remain reviewable; avoid noisy or speculative commits that were not validated.

### Commit policy

Commit only after:

- issue-specific tests pass
- core regression suite passes

Suggested commit message format:

```text
fix(issue-123): prevent stale session reads after invalidation
```

or

```text
feat(issue-241): add null-safe parser fallback
```

## 8. Validation Policy

Validation is tiered.

### Tier 1: Issue-specific validation

These commands are tied directly to the issue and must always pass.

Examples:

- `pytest tests/foo/test_bug.py -q`
- `npm test -- src/foo.spec.ts`
- `go test ./pkg/foo -run TestRaceCondition`

### Tier 2: Core regression validation

These commands are broader and protect critical system behavior. They must also pass before a change is retained.

Examples:

- auth smoke tests
- key API tests
- one essential integration test set

### Tier 3: Full validation

This is optional during each attempt and should usually be reserved for:

- branch promotion
- nightly wrap-up
- high-confidence candidate branches

The default operating mode for the first version is:

- Tier 1 required
- Tier 2 required
- Tier 3 optional

## 9. Execution Loop

The overnight engine should run the following state machine for each issue:

1. **Select issue**
   Choose the highest-priority ready execution issue.

2. **Prepare workspace**
   Check out the issue branch or create it from the configured base branch.

3. **Load context**
   Read the issue contract, latest logs, modified files, recent failures, and current test state.

4. **Plan a minimal attempt**
   Choose one concrete sub-problem to address. Avoid mixing unrelated changes.

5. **Edit**
   Modify only allowed paths.

6. **Run validation**
   Run Tier 1, then Tier 2.

7. **Decide**
   - If validation passes: commit and mark progress.
   - If validation fails with an obvious local mistake: apply a bounded retry.
   - If repeated attempts fail or scope expands: suspend the issue.

8. **Record**
   Write attempt data to local logs and update issue-visible status.

9. **Rotate**
   Continue the same issue only if there is still room for bounded progress. Otherwise pick the next issue.

## 10. Failure and Retry Policy

This is the main protection against wasted overnight time.

### Recommended defaults

- Maximum quick retries for the same local mistake: `2`
- Maximum failed attempts for one issue in one run: `5`
- Maximum consecutive no-progress attempts before suspension: `3`
- Per-command timeout: repository-specific, but must be explicit

### Failure classes

1. **Local recoverable**
   Examples:
   - syntax error
   - missing import
   - failing assertion caused by a small oversight

   Action:
   - retry quickly

2. **Scope expansion**
   Examples:
   - the issue is bigger than described
   - fixing it requires redesign across multiple modules

   Action:
   - suspend the issue and write a blocker summary

3. **Environment or infrastructure failure**
   Examples:
   - flaky CI dependency
   - database service unavailable
   - missing credentials

   Action:
   - suspend with infrastructure reason

4. **Repeated semantic failure**
   Examples:
   - the agent keeps trying equivalent fixes
   - new attempts do not improve test outcomes

   Action:
   - suspend and rotate

## 11. Anti-Cheating Rules

The framework must explicitly forbid:

- deleting tests only to make the suite pass
- weakening assertions without issue justification
- skipping required validation commands
- editing files outside allowed paths
- merging branches automatically
- repeating equivalent failed strategies indefinitely

If `can_edit_tests` is `false`, the agent must treat test files as read-only for that issue.

## 12. Local State Store

Local structured state should be the source of truth for continuity and analytics.

Suggested layout:

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
    issues/
      123.json
      241.json
```

### Suggested `night-run.json` shape

```json
{
  "run_date": "2026-03-26",
  "base_branch": "main",
  "started_at": "2026-03-26T22:00:00Z",
  "ended_at": null,
  "issues_attempted": [123, 241],
  "issues_completed": [],
  "issues_blocked": [123],
  "active_branches": ["overnight/issue-123-fix-cache-race"],
  "commits_created": ["abc1234"],
  "status": "running"
}
```

### Suggested per-issue log shape

```json
{
  "issue_id": 123,
  "branch": "overnight/issue-123-fix-cache-race",
  "status": "blocked",
  "attempts": [
    {
      "attempt": 1,
      "goal": "reproduce race with deterministic fixture",
      "files_touched": ["src/session/store.py", "tests/session/test_invalidation.py"],
      "tier1_passed": false,
      "tier2_passed": false,
      "outcome": "retry",
      "error_summary": "NameError in helper fixture"
    }
  ],
  "latest_summary": "Blocked after repeated semantic failures; likely requires broader locking redesign."
}
```

## 13. Human-Facing Synchronization

The issue tracker should be updated for readability, but not treated as the system of record.

Recommended visible updates:

- branch name
- latest commit
- current status
- short blocker summary
- next suggested action

The agent may also prepare a PR draft body or a review summary, but merge decisions must stay human-owned.

## 14. Prompt Responsibilities

The agent prompt should not try to contain the whole system. It should only encode the operating contract:

- You work on one normalized execution issue at a time.
- You may only edit allowed files.
- You must run required validation before keeping a change.
- You must suspend rather than spin when progress stops.
- You must leave a clear summary for the next human reviewer.

The prompt is an interpreter of the framework, not a substitute for issue structure, logging, validation policy, or branch isolation.

## 15. Version 1 Recommendation

The first implementation should stay local-first and simple.

### Include in V1

- issue files on disk
- branch-per-issue workflow
- required Tier 1 and Tier 2 validation
- local structured logs
- morning summary generation
- bounded retry and suspension logic

### Exclude from V1

- automatic merging
- multi-agent parallel execution
- automatic issue creation against a remote system
- dynamic reprioritization based on external signals
- heavyweight dashboards

## 16. Future Upgrades

After the basic loop is stable, the framework can evolve toward:

- automatic conversion from `overnight_tasks.md` into normalized issues
- GitHub issue and PR synchronization
- branch promotion rules using Tier 3 full validation
- duplicate-failure detection
- issue difficulty scoring
- resumable runs across multiple nights
- multi-agent scheduling for independent issue branches

## 17. Recommended Next Deliverables

The next implementation artifacts should be:

1. `overnight/config.yaml`
   Central policy for retries, timeouts, branch naming, and base branch.

2. `overnight/issues/*.yaml`
   Normalized issue definitions.

3. `overnight/program.md`
   The execution protocol given to Codex or Claude Code.

4. `scripts/run_overnight.py` or equivalent shell runner
   Orchestrates queue selection, branch setup, logging, and loop control.

5. `runs/<date>/summary.md`
   Human-readable morning report.

## 18. Decision Summary

The framework recommended by this design is:

- issue-driven, not free-form backlog-driven
- branch-isolated per issue
- local structured state as source of truth
- Tier 1 plus Tier 2 validation as the default merge gate for retained progress
- bounded retries with suspension and rotation
- human-reviewed integration in the morning

This provides a realistic path to overnight coding in ordinary repositories without over-optimizing for prompt cleverness.
