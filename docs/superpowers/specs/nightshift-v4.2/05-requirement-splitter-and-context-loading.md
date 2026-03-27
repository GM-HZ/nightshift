# 05. Requirement Splitter And Context Loading

## Purpose

This document defines the daytime decomposition flow and the repository context strategy that supports it.

Requirement Splitter is intentionally outside the stable kernel, but it is still a critical product capability.

## Splitter Responsibilities

- accept a large requirement or backlog area
- inspect repository context under explicit budgets
- propose issue-sized work units
- classify each proposal as execution, planning, repro, or investigation
- present proposals for human approval
- emit normalized issue contracts only after approval

## Input Forms

Supported input forms should include:

- free-form requirement text
- requirement file
- issue tracker selection
- repository-local backlog file

## Output Forms

The splitter should output proposals containing:

- title
- description
- suggested kind
- suggested allowed paths
- suggested validation strategy
- suggested acceptance
- notes on risk or dependency

## Repository Context Strategy

### Layer 0: Cheap Metadata

Always read:

- top-level file tree summary
- README and key docs
- package or build manifests
- test directory layout
- CI configuration summary if present
- language and framework signals

### Layer 1: Relevant Anchors

Read selectively based on requirement keywords:

- candidate modules
- likely entrypoints
- likely test files
- configuration files near target modules
- recent change hotspots when available

### Layer 2: Focused Deep Reads

Read only when Layer 0 and Layer 1 are insufficient:

- concrete implementation files
- local call chains
- schema or API contracts
- domain-specific design docs

### Layer 3: Cached Summaries

Persist compressed repository summaries so repeated splitting sessions do not pay the same full analysis cost.

## Budget Rules

The splitter must run under:

- a file-read budget
- a token budget
- a time budget

When budgets are exhausted, the splitter should:

- degrade gracefully
- produce lower-confidence suggestions
- mark items for human refinement instead of guessing

## Quality Gates

Before a proposal becomes an execution issue, the splitter or reviewer must verify:

- executable validation exists or can be stated concretely
- scope is bounded
- path constraints are plausible
- the issue is not secretly dependent on another unfinished issue

If those gates fail, the output should be:

- planning issue
- repro issue
- investigation issue

not execution issue.

## Human Approval Rule

The splitter can propose. It cannot approve.

Only human-approved issue contracts may enter the execution queue.

## Context Loader Reuse

The repository context loader should be reusable by:

- Requirement Splitter
- Engine context packer
- future search or triage tools

This is a shared infrastructure module, not a splitter-only helper.
