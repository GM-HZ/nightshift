# Documentation Information Architecture

## Status

Working product design for the current NightShift repository.

This document defines how NightShift documentation should be organized so the repository reads like a usable product, not only like an implementation diary.

## Why This Exists

The repository now contains:

- active architecture specs
- implementation-era walkthroughs
- rehearsal reports
- local development notes
- product workflow design docs

All of that information is useful, but the current entry experience is still too record-oriented.

The main pain points are:

- `README.md` carries too many responsibilities
- implementation notes and user guidance are mixed together
- historical and normative docs sit too close to first-time user entry points
- product workflow has advanced beyond the old kernel-era walkthrough shape

NightShift now needs a documentation structure that separates:

- product entry
- practical usage
- architecture and design
- historical reference

## Design Goal

A new reader should be able to answer these questions quickly:

1. What is NightShift?
2. What can it do today?
3. How do I install and use it?
4. Where do I read the architecture?
5. Where do I find formal specs and historical records?

## Recommended Documentation Zones

NightShift docs should be organized into four clear zones:

1. repository root `README.md`
2. `docs/usage/`
3. `docs/architecture/`
4. `docs/reference/` or the existing spec-and-history area

## Zone 1: Root README

`README.md` should become the product front door.

It should answer only the most immediate questions:

- what NightShift is
- what the current workflow can do
- the shortest path to trying it
- where to go next

### README Should Include

- one-paragraph product description
- current status summary
- very short feature list
- minimal quickstart
- links to usage docs
- links to architecture docs
- links to specs and historical reference

### README Should Avoid

- detailed implementation history
- long MVP caveat lists
- deep spec walkthroughs
- local debugging notes
- rehearsal transcripts

Those belong elsewhere.

## Zone 2: Usage Docs

`docs/usage/` should be the operator-facing and adopter-facing documentation area.

This is where someone learns how to actually run NightShift.

### Recommended Files

- `docs/usage/README.md`
- `docs/usage/install.md`
- `docs/usage/configuration.md`
- `docs/usage/workflow.md`
- `docs/usage/deployment.md`

### Responsibilities

#### `docs/usage/README.md`

Usage entry point and reading guide.

#### `docs/usage/install.md`

Installation and environment setup.

It should cover:

- Python installation expectations
- editable install or packaged install
- required external binaries
- basic verification commands

#### `docs/usage/configuration.md`

User-facing configuration guidance.

It should explain the intended model:

- user `~/.nightshift/`
- project `.nightshift/`
- current MVP compatibility with `nightshift.yaml`

#### `docs/usage/workflow.md`

The main end-to-end operator guide.

It should describe the real workflow in product terms, for example:

`requirement -> split -> approve -> execution branch -> work order -> draft PR -> ingest/materialize -> queue -> run -> deliver`

#### `docs/usage/deployment.md`

How to prepare NightShift for team or repo usage.

It should cover:

- tokens and auth
- engine prerequisites
- git/GitHub expectations
- basic operator setup

## Zone 3: Architecture Docs

`docs/architecture/` should remain the design and system model area.

It is for readers asking:

- how is NightShift structured?
- what is kernel vs product workflow?
- what are the active models and boundaries?

### Current Architecture Area Should Continue To Hold

- kernel and product boundaries
- coverage matrix
- execution work order model
- config and workspace model
- future information-model and workflow docs

This area should stay conceptual and structural, not procedural.

## Zone 4: Reference And History

NightShift still needs a place for:

- formal specs
- design history
- rehearsal artifacts
- workflow verification reports
- migration-era notes

The repository already has this information under:

- `docs/superpowers/specs/`
- `docs/rehearsals/`
- individual report files in `docs/`

The long-term direction should be to make this clearly read as reference/history rather than first-use guidance.

This can be achieved either by:

- introducing `docs/reference/` as an entry point, or
- keeping the current locations but linking to them under a clearly labeled reference section

The immediate redesign does not require moving every file.

## Immediate Reorganization Plan

The first pass should be intentionally conservative.

### Step 1

Rewrite `README.md` as a product front door.

### Step 2

Create `docs/usage/` and move operator-facing guidance there.

### Step 3

Keep `docs/architecture/` as the design entry point and continue adding model docs there.

### Step 4

Treat existing workflow verification and rehearsal material as reference/history, not as main entry docs.

## What Happens To Current Docs

### `docs/mvp-walkthrough.md`

This should no longer be the main usage guide.

Its content should be mined into `docs/usage/workflow.md`, then either:

- retained as historical MVP guidance, or
- folded into reference material

### `docs/local-development.md`

This should remain useful, but should be positioned as contributor/developer guidance rather than product entry.

It should likely be linked from usage install docs and contributor-facing docs rather than from the root README as a primary entry.

### Workflow Verification Reports

These should remain preserved, but clearly labeled as:

- verification evidence
- rehearsal history

not as usage guides.

## Tone Guidance

The new docs should read less like a lab notebook and more like a real tool.

That means:

- shorter front-door docs
- fewer exhaustive caveat lists in entry points
- stronger separation between user guidance and design history
- more direct task-based guidance

## Recommended Reading Paths

### New User

`README.md -> docs/usage/README.md -> docs/usage/install.md -> docs/usage/workflow.md`

### Operator

`README.md -> docs/usage/configuration.md -> docs/usage/workflow.md -> docs/usage/deployment.md`

### Architect Or Maintainer

`docs/architecture/README.md -> specific architecture model docs -> docs/superpowers/specs/`

### Research Or Audit Reader

`docs/rehearsals/` and `docs/superpowers/specs/`

## Relationship To Current Design Work

This information architecture depends on the newer product-side models:

- execution work order information model
- config and workspace model
- coverage matrix

Those models should inform how the new README and usage docs are written.

## Deferred Questions

This document does not yet define:

- the final wording of the new README
- exact migration of every legacy doc
- whether contributor docs should later become their own `docs/development/` area

Those should be handled during the documentation rewrite itself.
