# NightShift Product MVP: Issue Ingestion

## Purpose

This document defines the first product-layer issue-ingestion slice above the verified kernel baseline.

The goal is to remove manual hand-authoring of `IssueContract` and `IssueRecord` while still staying compatible with the `v4.2.1` architecture rules.

This slice is intentionally narrower than a full requirement splitter or full GitHub-to-PR automation flow.

## Scope

This MVP covers:

- GitHub issue as the primary external work-item source
- a NightShift issue template
- provenance checks
- admission checks
- materialization into:
  - immutable `IssueContract`
  - current `IssueRecord`
- compatibility with executing a selected issue list or all admitted issues

Current implementation status in this repository:

- implemented: strict template parsing
- implemented: provenance gate
- implemented: admission gate
- implemented: materialization into `IssueContract` and `IssueRecord`
- implemented: single-issue CLI entrypoint `nightshift issue ingest-github`
- not yet implemented: selected/all batch admission and execution loop

This MVP does not cover:

- free-form requirement splitting inside NightShift
- automatic decomposition from one requirement into many issues
- proposal review UI
- PR dispatch or merge automation
- notification workflows

## Design Position Relative To V4.2.1

This design preserves the core V4.2.1 rules:

- execution issues must be execution-ready
- required contract fields must resolve concretely
- verification must be executable, not vague prose
- the system must not silently invent missing execution fields

What changes here is the product experience, not the architecture rule:

- instead of exposing an explicit proposal-review-normalize flow to the user in the first MVP
- the system uses a stricter GitHub issue template plus gates
- issues that pass those gates are materialized directly into `IssueContract` and `IssueRecord`
- issues that fail the gates are rejected with explicit missing-field or provenance errors

## Product Flow

The product-layer flow is:

`GitHub issue -> provenance gate -> admission gate -> materialize -> queue/run`

This is deliberately narrower than:

`external requirement -> splitter -> proposal review -> normalized contract -> queue/run`

The latter still belongs to the broader product workflow and may be added later.

## Input Source

Primary source:

- GitHub issue

Expected source repository:

- a configured GitHub repository such as `GM-HZ/nightshift`

Expected local execution repository:

- a checked out local repository that contains `nightshift.yaml`

## GitHub Issue Template

The MVP requires a standard NightShift issue template.

Recommended sections:

- `Background`
- `Goal`
- `Allowed Paths`
- `Non-Goals`
- `Acceptance Criteria`
- `Verification Commands`
- `Notes`

Example shape:

```md
## NightShift Metadata
- NightShift-Issue: true
- NightShift-Version: product-mvp

## Background
...

## Goal
...

## Allowed Paths
- README.md
- README.zh-CN.md

## Non-Goals
- ...

## Acceptance Criteria
- ...
- ...

## Verification Commands
- python3 -c "..."
- python3 -c "..."

## Notes
...
```

The template is not just documentation. It is the structured source for ingestion.

## Provenance Gate

NightShift must not ingest arbitrary GitHub issues just because they happen to resemble the template.

An issue is eligible for ingestion only if all of the following pass:

### 1. Author Allowlist

The issue author must be in a repository-local allowlist.

Suggested config location:

- `nightshift.yaml.product.issue_ingestion.allowed_authors`

### 2. Required Label

The issue must contain a required label:

- `nightshift`

Suggested config location:

- `nightshift.yaml.product.issue_ingestion.required_label`

### 3. Template Marker

The issue body must contain explicit NightShift markers:

- `NightShift-Issue: true`
- `NightShift-Version: ...`

This prevents accidental ingestion of unrelated issues.

If any provenance condition fails:

- no contract is generated
- no issue record is generated
- the command returns a structured rejection reason

## Admission Gate

If provenance passes, NightShift performs execution-readiness checks.

The issue may materialize into `kind=execution` only if all of the following resolve concretely:

- `title`
- `goal`
- `allowed_paths`
- `acceptance`
- `verification commands`
- `priority`
- `forbidden_paths`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`

### Resolution Sources

- `title`
  from GitHub issue title
- `goal`
  from the template `Goal` section
- `allowed_paths`
  from the template `Allowed Paths` section
- `acceptance`
  from `Acceptance Criteria`
- `verification`
  from `Verification Commands`
- `priority`
  from a template field if present, otherwise `nightshift.yaml.issue_defaults.default_priority`
- `forbidden_paths`
  from `nightshift.yaml.issue_defaults.default_forbidden_paths`
- `test_edit_policy`
  from `nightshift.yaml.issue_defaults.default_test_edit_policy`
- `attempt_limits`
  from `nightshift.yaml.issue_defaults.default_attempt_limits`
- `timeouts`
  from `nightshift.yaml.issue_defaults.default_timeouts`

### No Silent Guessing Rule

If required execution fields are missing or too vague:

- the issue is rejected by admission
- it is not materialized as an execution contract
- the command returns explicit unresolved fields

This preserves the V4.2.1 execution boundary.

## Materialization

If both provenance and admission pass, NightShift writes:

- `nightshift/issues/<issue_id>.yaml`
- `nightshift-data/issue-records/<issue_id>.json`

### Generated `issue_id`

The MVP should use a deterministic local identifier scheme derived from the external issue:

- recommended format: `GH-<issue_number>`

Example:

- GitHub issue `#123` -> `GH-123`

This keeps the local immutable contract identity stable and easy to audit.

### `IssueContract`

Materialized as:

- `kind=execution`
- immutable after write
- fully normalized

### `IssueRecord`

Materialized as:

- `issue_state=ready`
- `attempt_state=pending`
- `delivery_state=none`
- `queue_priority` initialized from contract priority

## CLI Surface

Recommended initial commands:

- `nightshift issue ingest-github --repo-full-name <owner/repo> --issue <n> --target-repo /path/to/local/repo`
- `nightshift issue ingest-github --repo-full-name <owner/repo> --issue <n1,n2,n3> --target-repo /path/to/local/repo`

Recommended outputs:

- success:
  - local `issue_id`
  - materialized file paths
- rejection:
  - provenance failures
  - unresolved admission fields

## Execution Relationship

The ingestion slice should plug into execution without inventing a new queue abstraction.

Execution entry points should remain:

- `nightshift run-one <issue_id>`
- future `nightshift run --issues <id1,id2,...>`
- future `nightshift run --all`

The product-layer contract is:

- ingestion produces execution-ready local issues
- kernel consumes those local issues

## `run --issues` vs `run --all`

This ingestion MVP should be designed to support both future modes:

### `run --issues`

Use when a human wants explicit control over which admitted issues execute tonight.

### `run --all`

Use when the system should execute every admitted and schedulable issue.

The ingestion slice itself does not decide execution order. It only materializes execution-ready local work items.

## Failure Modes

Expected rejection classes:

- GitHub issue not found
- author not allowlisted
- required label missing
- NightShift template marker missing
- required sections missing
- allowed paths missing
- verification commands missing
- malformed verification commands
- local issue id collision
- local contract already exists with conflicting content

These should all fail closed.

## Repository-Local Configuration

Suggested new config area:

```yaml
product:
  issue_ingestion:
    enabled: true
    allowed_authors:
      - GM-HZ
    required_label: nightshift
```

This keeps provenance policy repository-local and explicit.

## Phase Boundary

This slice is still product workflow, not kernel.

It should be implemented above the kernel and should depend on:

- GitHub issue fetch
- template parsing
- provenance checks
- admission checks
- `Issue Registry` writes

It should not modify kernel execution semantics.

## Non-Goals For This Slice

- automatic splitting from one free-form requirement into multiple issues
- internal NightShift proposal review UI
- auto-generation of GitHub issues from spoken requirements
- PR creation or merge
- queue scheduling policy

Those remain future product-workflow slices.
