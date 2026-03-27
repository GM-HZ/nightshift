# 07. Language And Phasing

## Purpose

V4.2.1 keeps the V4.2 language recommendation and tightens the phasing semantics around reporting.

Base source:

- [../nightshift-v4.2/07-language-and-phasing.md](../nightshift-v4.2/07-language-and-phasing.md)

Where this document adds rules, it supersedes the V4.2 text.

## Language Recommendation

The language recommendation is unchanged:

- use **Python** for the NightShift kernel and CLI harness
- optionally add **TypeScript** later for dashboard or web control plane work

## Phasing Clarification

V4.2 created an ambiguity:

- `report generator` was listed in the later product-workflow phase
- the phasing rule also required a trustworthy morning report before edge modules

V4.2.1 resolves this by splitting reporting into two layers.

## Minimal Kernel Report

A minimal trustworthy morning report is part of the kernel-complete path, not an optional later edge module.

Its job is to produce a dependable run summary from:

- run state
- run-scoped issue snapshots
- attempt records
- event history
- alert history

Current `IssueRecord` snapshots are for live queue and status views.

Historical morning reports for a specific run must read the targeted run's persisted history, not the latest live issue state.

Minimum contents:

- run duration
- accepted issues
- blocked issues
- deferred issues
- retry summary
- artifact locations

This report may be plain Markdown or JSON and does not require rich formatting or provider integrations.

## Rich Report Generator

The later `Report Generator` edge module is an enhancement layer over the minimal kernel report.

It may add:

- richer formatting
- ranking and presentation polish
- PR/provider links
- cross-run comparisons
- more operator-friendly summaries

This resolves the phase conflict without moving a presentation-heavy module into the stable kernel.

## Revised Delivery Phasing

### Phase 1: Kernel Skeleton

- domain model
- state store
- issue registry
- run orchestrator shell
- workspace manager

### Phase 2: Engine, Validation, And Kernel Completion

- Codex adapter
- Claude Code adapter
- validation gate
- rollback and retry logic
- recovery after interruption
- minimal kernel report

### Phase 3: Product Workflow

- requirement splitter
- rich report generator
- notifications
- PR dispatcher

### Phase 4: Expansion

- dashboards
- provider integrations
- dependency-aware scheduling
- parallel execution

## Phasing Rule

Do not build Phase 3 edge modules before the kernel can:

- run one issue end to end
- reject safely
- recover after interruption
- produce a trustworthy minimal morning report
