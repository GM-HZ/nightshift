# Execution Work Order Information Model

## Status

Working product design aligned to `v4.2.1`.

This document does not replace the `v4.2.1` spec set. It tightens the product-side handoff model above the kernel.

## Why This Exists

The current product workflow already proved that NightShift can run a full chain:

`requirement -> split -> publish issue -> ingest -> queue -> run -> deliver -> PR`

What still feels awkward is the handoff surface between planning and execution.

If too much meaning lives only in GitHub issue text, comments, or external links, the system becomes fragile:

- agents may miss key execution constraints
- humans cannot reliably reconstruct why a change happened
- branch-local artifacts can be lost before merge
- execution information gets scattered across tools and URLs

NightShift needs one explicit model for:

- human review and traceability
- machine execution
- git-native collaboration before merge

## Design Goal

NightShift should treat the execution input as a first-class artifact, not as an overloaded GitHub issue.

That artifact must:

- be visible to collaborators before code is merged
- live in the repository during execution
- retain git history when updated
- provide a stable machine-readable execution block
- preserve enough rationale for later review and maintenance

## Recommended Model

Use a layered handoff model:

`Requirement Issue -> Proposal -> Execution Branch + Execution Work Order -> Draft PR -> IssueContract -> Run -> Delivery PR -> Archive`

### Layer Roles

#### Requirement Issue

This is the problem statement and discussion surface.

It may include:

- background
- user need
- product discussion
- references
- decomposition notes

It is not the final night-run execution source.

#### Proposal

This is the splitter output.

It is a candidate implementation slice that still needs review and publication.

It may be edited, approved, rejected, or split further.

#### Execution Branch

Each execution slice gets its own branch.

That branch becomes the active git context for:

- the execution work order
- the code changes
- the draft PR review surface

Each execution branch should have exactly one primary work order.

#### Execution Work Order

This is the core execution information source for NightShift.

It is the approved implementation workbook for one execution slice.

It lives in the execution branch and is published through the draft PR so that it is visible before merge.

It is the source NightShift should materialize into an immutable `IssueContract`.

#### Draft PR

The draft PR is the shared review surface for the execution branch.

It makes the work order visible to the team immediately and guarantees that later changes to the work order are tracked in git history.

The draft PR is where reviewers inspect:

- the work order
- scope changes
- implementation progress

#### IssueContract

This remains the NightShift-internal immutable runtime contract.

It should be materialized from the approved machine-readable portion of the execution work order.

#### Run / Delivery

Runtime records and delivery state remain separate from the work order.

They record what actually happened, not what was intended.

## Core Principle

Anything an overnight agent must know in order to execute safely must exist inside the repository and be reachable from the execution branch.

External URLs may exist as references, but they must not be the only source of decisive execution information.

## File Placement

### Active Work Order

During execution, the work order should live at:

`.nightshift/work-orders/WO-<id>.md`

### Archived Work Order

After merge, the work order should move to:

`.nightshift/archive/work-orders/YYYY/MM/WO-<id>.md`

This keeps the active path clean while preserving long-term repository traceability.

## File Format

Use Markdown with YAML frontmatter.

This balances:

- good PR reading experience for humans
- stable field extraction for NightShift
- single-file maintenance

## Internal Structure

The work order file has two semantic sections:

1. `execution`
2. `rationale`

NightShift should only materialize the `execution` block into the runtime contract.

The `rationale` block exists for review, maintenance, and historical understanding.

## Example Shape

```md
---
work_order_id: WO-20260329-001
status: approved
source_issue:
  repo: GM-HZ/nightshift
  number: 7
  url: https://github.com/GM-HZ/nightshift/issues/7
execution:
  title: Add Chinese README
  goal: Add a Chinese README and link it from the main README.
  allowed_paths:
    - README.md
    - README.zh-CN.md
  non_goals:
    - Change packaging
    - Rewrite unrelated docs
  acceptance_criteria:
    - README.zh-CN.md exists and is non-empty
    - README.md links to README.zh-CN.md
  verification_commands:
    - test -s README.zh-CN.md
    - rg -n "README\\.zh-CN\\.md" README.md
  context_files:
    - README.md
  constraints:
    - Keep terminology aligned with existing NightShift docs
  engine_hints:
    primary: codex
rationale:
  summary: Add a Chinese entry point without expanding scope into a full docs rewrite.
  risks:
    - Terminology drift from existing product docs
  notes:
    - Follow current README tone and structure
---

# Execution Work Order

## Background

...

## Implementation Notes

...

## Review Notes

...
```

## Field Semantics

### Frontmatter Fields That NightShift Must Trust

NightShift should read only these structured fields when materializing an `IssueContract`:

- `work_order_id`
- `status`
- `source_issue`
- `execution.title`
- `execution.goal`
- `execution.allowed_paths`
- `execution.non_goals`
- `execution.acceptance_criteria`
- `execution.verification_commands`
- `execution.context_files`
- `execution.constraints`
- `execution.engine_hints`

NightShift must not infer contract fields from prose paragraphs in the body.

### Frontmatter Fields For Humans And Audit

`rationale` is intentionally structured, but it is not part of contract materialization.

It exists to capture:

- why this slice exists
- what tradeoffs were chosen
- what a later maintainer should understand

### Markdown Body

The body is for review clarity.

It may include:

- background
- implementation notes
- review notes
- links to supporting material

The body is never the only source of required execution fields.

## Relationship To GitHub

### Requirement Issue

The requirement issue remains the upstream discussion anchor.

It should link to the draft PR once the execution branch exists.

### Draft PR

The draft PR becomes the shared execution surface.

Its description should reference:

- the source requirement issue
- the work order file path

### Delivery PR

The same PR should continue through implementation and delivery when possible.

NightShift should avoid creating a separate disconnected PR for execution artifacts and implementation results unless the workflow explicitly requires that split.

## Lifecycle

### 1. Planning

NightShift creates proposals from a requirement.

### 2. Publication

An approved proposal creates:

- an execution branch
- an execution work order file
- a draft PR

### 3. Materialization

NightShift ingests the approved `execution` block and creates the immutable runtime contract.

### 4. Execution

NightShift runs the issue using the execution branch and contract.

### 5. Delivery

NightShift updates the same PR with the accepted code result.

### 6. Archive

After merge, the work order moves to the archive path.

## Why This Is Better Than Overloading GitHub Issues

This model keeps each artifact focused:

- issue: why the work exists
- proposal: how to slice it
- work order: how to execute it safely
- contract: what NightShift actually runs
- run records: what really happened

That separation reduces drift and makes the system easier to audit.

## Relationship To `v4.2.1`

This model stays aligned with `v4.2.1`:

- splitter remains outside the kernel
- review still exists before execution
- immutable contract still exists
- runtime history remains separate from planning artifacts

What changes is the product-side handoff surface:

- from a heavily overloaded GitHub issue
- to a git-native execution branch and work order published through a draft PR

## Deferred Questions

This document does not yet define:

- exact CLI commands for creating execution branches and draft PRs
- how work order editing permissions are enforced
- how configuration and credentials move to `~/.nightshift/` and project `.nightshift/`
- whether one delivery PR can ever contain more than one work order

Those should be handled by follow-up product design docs.
