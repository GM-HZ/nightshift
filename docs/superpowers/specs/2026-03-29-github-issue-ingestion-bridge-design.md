# GitHub Issue Ingestion Bridge Design

## Goal

Restore a live GitHub-based planning entry surface without undoing the newer execution-work-order model.

This slice adds back a GitHub intake path, but it does **not** return to the older issue-centric runtime model.

The target bridge is:

`GitHub issue -> ingestion gate -> Execution Work Order -> queue add -> IssueContract`

## Why This Design

The repository now has a stronger execution model than the older product MVP:

- execution work orders are the approved execution source
- `queue add` is the freeze point
- `IssueContract` is generated from the work order, not directly from a planning issue

So GitHub issue ingestion should return as a **bridge into the work-order path**, not as a parallel execution path.

## Scope

In scope:

- `nightshift issue ingest-github`
- GitHub issue fetch
- provenance gate
- admission gate
- mapping into `.nightshift/work-orders/WO-<id>.md`
- support for creating a new work order from a compliant GitHub issue

Out of scope:

- automatic `queue add`
- automatic `run`
- delivery / PR automation
- splitter / proposal workflow
- Draft PR creation from the ingested issue
- free-text intelligent inference for missing required execution fields

## Core Rule

GitHub issue ingestion does **not** create an `IssueContract`.

It creates or updates an `Execution Work Order`.

`queue add` remains the only freeze/materialization point.

## Command Shape

First version command:

```bash
nightshift issue ingest-github \
  --repo-full-name GM-HZ/nightshift \
  --issue 42 \
  --repo /path/to/local/repo
```

Suggested optional flags for first version:

- `--update-existing`
- `--branch` (if later needed for execution-branch targeting)

The first version should stay conservative and require explicit local repo context.

## Input Expectations

The source GitHub issue must be a NightShift-compatible planning artifact.

That means the issue must pass:

### Provenance Gate

- author is in the allowlist
- issue has the required `nightshift` label
- issue matches the standard NightShift issue template expectations

### Admission Gate

The issue must contain enough structured data to produce a valid execution work order.

Required mapped information:

- title
- goal
- allowed paths
- non-goals
- acceptance criteria
- verification commands or structured verification
- source issue metadata

If those fields are not present or are malformed, ingestion must fail cleanly.

## Output Shape

The command writes a repository-local execution work order at:

`.nightshift/work-orders/WO-<id>.md`

The work order should follow the existing Markdown + frontmatter model.

It should include:

- `work_order_id`
- `source_issue`
- `status`
- `execution`
- `rationale`

## Mapping Rules

### GitHub Issue -> Work Order Frontmatter

Map structured issue fields into work order frontmatter:

- issue title -> `execution.title`
- issue goal / summary -> `execution.goal`
- allowed paths -> `execution.allowed_paths`
- non-goals -> `execution.non_goals`
- acceptance criteria -> `execution.acceptance_criteria`
- verification -> `execution.verification` or `execution.verification_commands`
- source repo / issue number / url -> `source_issue`

### GitHub Issue -> Work Order Rationale / Body

Human-readable background and notes should go into:

- `rationale.summary`
- Markdown body sections when appropriate

But runtime materialization must still depend only on the work order `execution` block.

## Status After Ingestion

The resulting work order should not be treated as already frozen.

The expected post-ingestion path is:

1. ingest GitHub issue into work order
2. review/update work order if needed
3. run `queue add`
4. let `queue add` freeze and materialize the contract

This preserves the current execution model.

## Existing Work Order Behavior

If an execution work order already exists for the same source issue:

- default behavior should be safe and conservative
- first version should prefer failing with a clear message unless `--update-existing` is explicitly provided

This avoids silent drift in approved execution artifacts.

## Error Handling

The command should fail with short operator-friendly errors for:

- missing token / auth
- issue not found
- provenance gate failure
- missing required fields
- malformed verification shape
- attempted overwrite without explicit permission

No traceback-style user output for normal validation failures.

## Relationship To Current Architecture

This design intentionally preserves the newer architecture:

- GitHub issue is a planning-side source
- execution work order is the repository execution source
- `queue add` is the freeze point
- `IssueContract` is the immutable runtime artifact

So this slice is a planning-entry bridge, not a return to the older issue-centric execution model.

## Testing Expectations

The implementation should cover:

- compliant issue -> work order creation
- provenance gate rejection
- admission gate rejection
- duplicate/update behavior
- source issue metadata mapping
- verification mapping
- operator-friendly CLI output

## Success Criteria

This slice is successful when:

- GitHub issues are once again a live planning entry surface
- the resulting output fits the current execution-work-order path
- `queue add` remains the only contract freeze point
- the new planning bridge strengthens the current model instead of bypassing it
