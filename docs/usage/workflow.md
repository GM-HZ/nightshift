# Workflow

This page describes the real NightShift product flow in product terms.

The current system is usable today, but some steps still have MVP-shaped simplifications. The important part is the end-to-end order, not a perfect abstraction boundary.

## Current Flow

`requirement -> split -> proposals -> approve/update -> publish -> ingest -> queue add -> run -> deliver`

## Step By Step

### Requirement

A human starts with a change request, usually as a short problem statement or a repo issue description.

### Split

NightShift turns the requirement into one or more proposals.

This is implemented today, but the splitter is still intentionally thin. Treat the output as a reviewable starting point, not a high-quality decomposition guarantee.

### Proposals

Humans review the proposals, then update, approve, reject, or refine them.

This review loop exists today, but the interaction is still MVP-shaped compared with the target product direction.

### Publish

The approved proposal is published into the repository workflow, typically as a GitHub issue that NightShift can ingest.

The current product chain still uses GitHub issue publication as the practical handoff into execution.
The newer execution-branch and work-order model is an active design direction above that flow.

### Ingest

NightShift materializes the approved issue into its immutable contract plus the current mutable record.

This step is implemented today, but the semantics are still spread across the issue template, proposal shape, and contract fields.

### Queue Add

The issue enters the execution queue.

Current queue operations are available through the CLI:

```bash
nightshift queue add NS-123 --repo /path/to/repo
nightshift queue status --repo /path/to/repo
nightshift queue show NS-123 --repo /path/to/repo
nightshift queue reprioritize NS-123 high --repo /path/to/repo
```

### Run

NightShift executes queued work through the engine, validation, and recovery loop.

The main current commands are:

```bash
nightshift run --issues NS-123 --config /path/to/repo/nightshift.yaml
nightshift run --all --config /path/to/repo/nightshift.yaml
```

`run-one` still exists as a lower-level kernel-era command, but the product-facing flow should prefer `run`.

This path is implemented today and writes durable run state, attempts, and artifacts.

### Deliver

Accepted work is delivered back into the repository workflow as branch and pull-request state.

The current delivery commands are:

```bash
nightshift deliver --issues NS-123 --config /path/to/repo/nightshift.yaml
nightshift run --issues NS-123 --deliver --config /path/to/repo/nightshift.yaml
```

That delivery path exists today, but it is still simpler than the final product direction. For example, merge automation and richer PR policy are not part of the current baseline.

## What Is MVP-Shaped Today

- splitter quality is intentionally narrow
- review UX is still file- and CLI-driven
- execution semantics are clearer than the surrounding issue-to-contract handoff semantics
- delivery is functional, but not a full release-management system

## What To Use For Verification

If you want to confirm the current flow end to end, start with:

- [../2026-03-28-workflow-verification-report.md](../2026-03-28-workflow-verification-report.md)
- [../rehearsals/2026-03-29-gh7-product-e2e/README.md](../rehearsals/2026-03-29-gh7-product-e2e/README.md)
