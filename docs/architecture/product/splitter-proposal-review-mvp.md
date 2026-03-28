# NightShift Product MVP: Splitter And Proposal Review

## Purpose

This document defines the product-layer slice that sits before GitHub issue ingestion.

The goal is to let NightShift handle:

- a broader incoming requirement
- structured decomposition into candidate work items
- human review of those candidates
- promotion of approved candidates into standard NightShift GitHub issues

This is the missing upstream bridge for the product flow we have already implemented:

`GitHub issue -> ingest -> queue add -> run`

## Scope

This MVP covers:

- one higher-level requirement as input
- generation of one or more structured `SplitterProposal` items
- human review and approval of those proposals
- emission of approved items into standard NightShift GitHub issues
- compatibility with the current `issue ingest-github` flow

Current implementation status in this repository:

- implemented: local proposal batch persistence
- implemented: explicit review state transitions
- implemented: publish-ready validation
- implemented: proposal rendering into the standard NightShift GitHub issue template
- implemented: minimal CLI flow via `split`, `proposals show`, `proposals update`, `proposals approve`, `proposals reject`, and `proposals publish`
- implemented: real GitHub issue creation adapter
- not yet implemented: richer review UX or high-quality skill-backed decomposition

This MVP does not cover:

- direct emission of final immutable `IssueContract` from the splitter
- fully unattended decomposition and approval
- delivery / PR creation
- automatic merge
- dependency graph scheduling

## Design Position Relative To V4.2.1

This slice follows the core V4.2.1 rule:

- the splitter does not directly emit the final immutable `IssueContract`

Instead it emits proposal objects that must pass human review before becoming execution-ready work items.

V4.2.1 says:

- `SplitterProposal`
  is a human-review artifact
- `IssueContract`
  is the normalized immutable contract persisted after approval

For the product MVP, we refine that into a two-hop model:

`requirement -> SplitterProposal -> approved GitHub issue -> issue ingest-github -> IssueContract`

This preserves the architecture rule while still fitting our current implementation.

## Explicit Alignment With V4.2.1

This design is intended as a product-layer operationalization of V4.2.1, not a replacement for it.

The alignment points are:

- splitter remains outside the stable kernel boundary
- `SplitterProposal` remains a review artifact, not an immutable execution contract
- human review remains mandatory before execution-facing materialization
- execution-ready contract fields must still resolve concretely
- repository-local defaults in `nightshift.yaml` remain the canonical policy source
- the system still must not silently invent missing execution fields

What changes here is not the kernel architecture.

What changes is the product handoff path between planning and execution.

V4.2.1 describes:

`requirement -> proposal -> review -> normalization -> IssueContract`

This product design refines that into:

`requirement -> splitter skill artifact -> proposal review -> standard NightShift GitHub issue -> issue ingest-github -> IssueContract`

That refinement introduces three explicit product-side seams that V4.2.1 left abstract:

1. a splitter skill artifact protocol
2. GitHub issue as the durable operator-visible handoff between planning and execution
3. a split normalization path:
   - proposal review and publish gate
   - ingestion provenance and admission gate

These are product workflow clarifications.

They do not change the kernel contract model, recovery model, persistence model, or validation model defined by V4.2.1.

## Why GitHub Issues Remain The Product Boundary

We already chose GitHub issue as the main operator-visible work item.

That should remain true here.

So the splitter/proposal-review slice should not bypass GitHub issues and write contracts directly.

Instead:

- the splitter produces structured proposals
- human review approves or edits them
- the approved proposals are published as standard NightShift GitHub issues
- the existing ingestion path consumes those issues

That gives us one stable operator surface:

- GitHub issues are the durable, auditable handoff between planning and execution

## Product Flow

The product-layer flow becomes:

`requirement -> split -> proposals -> review -> approved GitHub issues -> ingest -> queue -> run`

This means the product stack has three distinct boundaries:

1. **planning boundary**
   requirement to proposals
2. **work-item boundary**
   approved proposals to GitHub issues
3. **execution boundary**
   GitHub issues to immutable contracts and current records

## Input Source

The first version should support one explicit source:

- a local requirement document or markdown file

This is the right MVP boundary because:

- it is stable
- it is auditable
- it decouples splitter design from voice/UI concerns

Future inputs may include:

- freeform CLI prompt
- issue collection
- meeting transcript
- external backlog item

But those should all eventually normalize into the same requirement input shape.

## Splitter Output

Each `SplitterProposal` should contain at least:

- proposal id
- title
- summary / description
- suggested kind
- suggested allowed paths
- suggested acceptance criteria
- suggested verification commands or verification notes
- notes on risks or dependencies
- confidence / review-needed notes

The key point is:

- proposal output is richer than a raw task list
- but it is still not a final execution contract

## Proposal Review

Proposal review is the human checkpoint between decomposition and executable work.

The human must be able to:

- accept a proposal
- reject a proposal
- edit a proposal
- merge or split proposals manually if needed

The MVP does not need a full UI.

A CLI- and file-based review flow is enough if it is explicit and auditable.

## Recommended MVP Review Shape

The first version should use:

- a generated local review bundle
- one file per proposal or one proposals file
- an explicit approval command after human edits

Suggested flow:

1. `nightshift split --file requirements/foo.md`
2. NightShift writes proposals into a local review directory
3. human edits/marks proposals
4. `nightshift proposals publish ...`
5. approved proposals become standard GitHub issues

This keeps the product flow reviewable without building a dedicated UI too early.

## Output Boundary: Standard NightShift GitHub Issue

Approved proposals must be emitted as the same standard NightShift issue template already expected by:

- `issue ingest-github`

That means proposal publishing is responsible for producing issue bodies containing:

- `NightShift-Issue: true`
- `NightShift-Version: product-mvp` or later version marker
- `Background`
- `Goal`
- `Allowed Paths`
- `Non-Goals`
- `Acceptance Criteria`
- `Verification Commands`
- `Notes`

This is important because it prevents the planning workflow from inventing a second execution-ingestion format.

## Review Gate

The publish step must fail closed unless all of the following are true:

- proposal is explicitly approved
- title is concrete
- goal is concrete
- allowed paths are present
- acceptance criteria are present
- verification commands are present or have been explicitly refined into executable form
- required provenance metadata for GitHub issue publication is available

If these are not true:

- do not publish the proposal as a NightShift execution issue

This preserves the same "no silent guessing" rule that exists at ingestion time.

## Provenance Relationship

Earlier we added provenance rules for GitHub issue ingestion:

- author allowlist
- required label
- template marker

The splitter/publish flow should integrate with those rules, not bypass them.

Recommended MVP approach:

- published issues are created by a NightShift-controlled actor
- published issues automatically receive the required `nightshift` label
- published issue bodies include the required template markers

That way, the issues generated by this upstream workflow already satisfy ingestion provenance.

## CLI Surface

Recommended first commands:

```bash
nightshift split --file requirements/feature-x.md
nightshift proposals show
nightshift proposals publish PROP-1 PROP-2
```

Possible later commands:

```bash
nightshift proposals reject PROP-3
nightshift proposals edit PROP-1
```

The first version should stay narrow:

- split
- inspect proposals
- publish approved proposals into GitHub issues

## Local Persistence

The first version should persist proposal review artifacts locally.

Suggested shape:

- `nightshift-data/proposals/<proposal_batch_id>/proposals.json`
- or `nightshift-data/proposals/<proposal_id>.json`

These are product-layer review artifacts, not kernel contracts.

They should remain editable and versionable until publication.

## Relationship To Queue Admission

The recommended operator path after publication is:

1. publish approved proposals as GitHub issues
2. `issue ingest-github`
3. optional `--materialize-only`
4. `queue add`
5. `run --issues` or `run --all`

This keeps each transition explicit:

- proposal approval
- issue publication
- contract materialization
- queue admission
- execution

## Failure Modes

Expected fail-closed classes:

- requirement too vague to split into safe proposals
- proposal missing paths or acceptance detail
- proposal missing executable verification
- proposal not explicitly approved
- issue publication failure
- duplicate publish attempt

These should all stop before execution-facing artifacts are produced.

## Phase Boundary

This slice remains firmly in product workflow.

It may depend on:

- splitter logic or agent skill
- local proposal persistence
- GitHub issue creation/publishing

It should not:

- directly mutate kernel execution state
- skip proposal review
- directly write final contracts as a substitute for GitHub issue publication

## Non-Goals For This Slice

- voice-driven requirement intake
- fully autonomous planning approval
- direct contract generation without issue publication
- delivery or PR dispatch
- merge automation

Those remain later product slices.
