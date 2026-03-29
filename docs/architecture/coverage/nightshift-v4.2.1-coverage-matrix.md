# NightShift V4.2.1 Coverage Matrix

## Purpose

This document maps the current repository against the `v4.2.1` design set.

It is not a historical spec and not a changelog.

It is an implementation-facing view that answers four questions:

1. what is fully implemented
2. what exists only as an MVP simplification
3. what is designed but not implemented
4. what still needs design tightening before implementation should continue

## Status Labels

- `implemented`
  The repository behavior matches the current design closely enough to treat it as live baseline behavior.
- `implemented-with-mvp-simplification`
  The capability exists and works, but only in a narrower form than the full `v4.2.1` product direction.
- `designed-not-implemented`
  The architecture/spec direction exists, but the capability is not present in code.
- `needs-design-tightening`
  The current capability exists or is partly designed, but the information model or boundary is not strong enough for confident expansion.

---

## 1. Kernel Coverage

### 1.1 Domain Model

- `IssueContract` immutable boundary: `implemented`
- `IssueRecord` as authoritative current mutable issue state: `implemented`
- `AttemptRecord` and `RunState` persistence split: `implemented`
- delivery linkage on `IssueRecord`: `implemented`
- current-state vs run-history truth split: `implemented`

Notes:

- the current code now respects the `IssueContract` vs runtime-state split
- run-scoped history and current issue state are separate in practice

### 1.2 Issue Registry

- contract save/load: `implemented`
- current record save/load: `implemented`
- schedulable listing: `implemented`
- queue reprioritization via current record: `implemented`
- delivery linkage attachment: `implemented`

Notes:

- current registry behavior is aligned with the V4.2.1 ownership rule

### 1.3 Run Orchestrator

- single issue execution via `run-one`: `implemented`
- validation-gated acceptance / rejection: `implemented`
- rollback on failure: `implemented`
- run-scoped persistence: `implemented`
- schedulability enforcement at orchestration boundary: `implemented`

Remaining simplification:

- no native multi-issue overnight daemon loop inside kernel, by design

### 1.4 Engine Adapter Layer

- Codex adapter: `implemented`
- Claude Code adapter: `implemented`
- normalized engine outcome handling: `implemented`
- non-interactive Codex invocation hardening: `implemented`

MVP simplification:

- no engine auto-fallback policy in the live harness
- schema fields for fallback still exist, but the harness intentionally executes one engine per attempt

### 1.5 Validation Gate

- issue validation: `implemented`
- regression validation: `implemented`
- static validation hook: `implemented-with-mvp-simplification`
- promotion validation hook: `implemented-with-mvp-simplification`

Notes:

- the gate exists and enforces required stages
- richer policy layering is still minimal

### 1.6 Workspace And Recovery

- isolated worktree execution: `implemented`
- rollback: `implemented`
- rerun-safe worktree reuse: `implemented`
- recovery into a new controlling run: `implemented`
- validating-boundary recovery: `implemented`

### 1.7 Minimal Kernel Report

- run-scoped historical report: `implemented`
- current-vs-historical truth separation: `implemented`

MVP simplification:

- report output is still minimal JSON, not rich operator presentation

### 1.8 Kernel Summary

Kernel status overall: `implemented`

Practical conclusion:

- the stable kernel defined by `v4.2.1` is present and has already passed real workflow rehearsal

---

## 2. Product Workflow Coverage

### 2.1 Splitter / Proposal Review

- local requirement file input: `implemented-with-mvp-simplification`
- proposal batch persistence: `implemented`
- proposal review states: `implemented`
- proposal update / approve / reject CLI: `implemented`
- publish into standard NightShift GitHub issue template: `implemented`
- real GitHub issue create adapter: `implemented`

Still simplified:

- current splitter is intentionally thin and not yet high-quality decomposition
- no richer review UX beyond CLI and file-backed review state
- no skill-backed structured context bundle flow yet

Status:

- overall: `implemented-with-mvp-simplification`

### 2.2 GitHub Issue Ingestion

- strict template parsing: `implemented`
- provenance gate: `implemented`
- admission gate: `implemented`
- materialization into `IssueContract` and `IssueRecord`: `implemented`
- `--materialize-only` review-first path: `implemented`

Known simplification:

- source linkage is currently embedded in `IssueContract.notes`, not a dedicated structured field

Status:

- overall: `implemented-with-mvp-simplification`

### 2.3 Queue Admission

- explicit `queue add`: `implemented`
- all-or-nothing admission: `implemented`
- idempotent ready/pending behavior: `implemented`
- draft-to-ready normalization: `implemented`
- queue priority mutation only on current record: `implemented`

Status:

- overall: `implemented`

### 2.4 Execution Selection

- `run --issues`: `implemented`
- `run --all`: `implemented`
- sequential fail-fast batch execution: `implemented`
- reuse of kernel `run-one`: `implemented`

Still simplified:

- no continue-on-failure
- no daemon mode
- no stop / pause / resume
- no dependency-aware scheduling

Status:

- overall: `implemented-with-mvp-simplification`

### 2.5 Delivery / PR Dispatcher

- explicit `deliver --issues`: `implemented`
- `run --deliver` convenience hook: `implemented`
- commit / push / PR create flow: `implemented`
- `IssueRecord` delivery linkage update: `implemented`
- real PR rehearsal: `implemented`

Still simplified:

- no merge automation
- no PR update / reopen policy
- no review-thread sync
- no reviewer / label policy
- accepted-result freezing is not implemented; delivery uses the current allowed-path worktree diff

Status:

- overall: `implemented-with-mvp-simplification`

### 2.6 Notifications

- notification adapter layer: `designed-not-implemented`
- operator alert delivery channels: `designed-not-implemented`

### 2.7 Rich Report Generator

- richer report presentation layer: `designed-not-implemented`
- cross-run comparisons: `designed-not-implemented`
- provider-linked operator report: `designed-not-implemented`

### 2.8 Overnight Control Loop

- unattended multi-issue daemon runner: `designed-not-implemented`
- stop / resume control loop: `designed-not-implemented`
- dependency-aware or slot-aware scheduling: `designed-not-implemented`

### 2.9 Product Workflow Summary

Product workflow status overall: `implemented-with-mvp-simplification`

Practical conclusion:

- the product chain is no longer theoretical
- `requirement -> split -> publish issue -> ingest -> queue -> run -> deliver -> PR` has been rehearsed successfully
- what remains is mostly depth, ergonomics, and policy richness, not absence of a usable product chain

---

## 3. Cross-Cutting Coverage

### 3.1 Information Model And Handoff Semantics

- `Requirement -> Proposal -> GitHub issue -> IssueContract` chain: `implemented-with-mvp-simplification`
- immutable contract boundary after materialization: `implemented`
- human review before execution-facing handoff: `implemented-with-mvp-simplification`

Needs tightening:

- execution issue semantics are still spread across issue template, proposal schema, and contract fields
- source linkage is not yet a first-class structured field
- accepted-result freezing for delivery is not yet modeled

Status:

- overall: `needs-design-tightening`

### 3.2 Config And Operator Environment

- repo-local YAML config: `implemented`
- product-side config sections for ingestion and delivery: `implemented-with-mvp-simplification`
- engine/token use via environment variables: `implemented-with-mvp-simplification`

Not yet implemented:

- home-directory vs project-directory config layering
- structured auth/token management
- user-level engine/profile configuration model
- project-local `.nightshift/` layout

Status:

- overall: `needs-design-tightening`

### 3.3 Docs And Onboarding

- architecture entrypoints: `implemented`
- product design docs per slice: `implemented`
- workflow verification report: `implemented`
- rehearsal archive: `implemented`

Still weak:

- top-level README is still closer to an engineering status document than a polished product entrypoint
- usage docs, architecture docs, and deployment/operator docs are not yet cleanly separated

Status:

- overall: `needs-design-tightening`

### 3.4 Deployment / Operations

- local developer workflow: `implemented-with-mvp-simplification`
- multi-worktree guidance: `implemented`

Not implemented:

- installation story for end users
- packaged deployment guidance
- service mode / host setup
- secrets management conventions

Status:

- overall: `designed-not-implemented`

---

## 4. What Is Actually Missing From V4.2.1

The biggest missing parts are not in the kernel.

The biggest missing parts are:

- richer splitter / skill-based decomposition quality
- stronger execution-issue information model
- structured source-link metadata
- accepted-result freezing before delivery
- home + project config model
- polished usage / architecture / deployment docs
- notifications
- richer reporting
- unattended overnight daemon workflow
- post-PR workflows such as review sync and merge automation

---

## 5. Recommended Next Design Order

Based on the current repository state, the cleanest next-order design work is:

1. information model and issue/contract handoff tightening
2. config and directory model redesign
3. README / usage / architecture / deployment doc rewrite
4. only then expand richer splitter or overnight policy

Reason:

- the repository already has a real usable chain
- the next risk is not "missing basic capability"
- the next risk is growing the product on top of soft handoff semantics and soft config boundaries

---

## 6. Bottom-Line Assessment

`v4.2.1` status in this repository is best described as:

- kernel: `implemented`
- product workflow: `implemented-with-mvp-simplification`
- cross-cutting operator model: `needs-design-tightening`

That means the project is past the stage of proving whether NightShift can work.

It now needs design refinement around:

- what the execution issue really is
- how information moves without human nighttime confirmation
- how operators configure and trust the tool
- how the repository explains itself to real users
