# Config And Workspace Model

## Status

Working product design aligned to `v4.2.1`.

This document refines the current configuration and workspace layout so NightShift can evolve from a single-file project tool into a stable agent operating layer.

## Why This Exists

The current repository still reflects an MVP-era layout:

- one main project config file
- separate `nightshift-data/` runtime state
- mixed assumptions about what belongs in git and what does not

That was acceptable while validating the kernel and first product workflows.

It is no longer the most ergonomic shape for a long-lived NightShift system.

NightShift now needs a clearer model for:

- user-level configuration
- project-level configuration
- execution work orders
- immutable contracts
- runtime-only state
- archives and reports

## Design Goal

NightShift should use a directory-based configuration and workspace model with clear responsibility boundaries.

The design should support:

- agent-friendly discovery
- safe separation of secrets from repo config
- git-native execution planning
- stable room for future growth

The first version does not need every directory to be implemented immediately.

It does need the architecture to be clean enough that later growth does not force a redesign.

## Top-Level Principle

NightShift should have two spaces:

- user space: `~/.nightshift/`
- project space: `<repo>/.nightshift/`

They serve different purposes and must not be mixed.

## User Space

User space is private, machine-scoped, and not committed to the repository.

Recommended root:

`~/.nightshift/`

### Responsibilities

User space holds:

- user defaults
- auth references
- provider and engine preferences
- local caches
- local logs
- global tool state

### Recommended Structure

```text
~/.nightshift/
  config/
  auth/
  engines/
  skills/
  plugins/
  cache/
  logs/
  state/
```

### Directory Meanings

#### `config/`

User-level defaults such as:

- preferred default engine
- default provider names
- default CLI behavior
- user-specific workflow preferences

#### `auth/`

Sensitive credentials and auth metadata such as:

- GitHub token references
- provider auth settings
- API endpoint credentials

This should be separate from ordinary user configuration.

#### `engines/`

Local engine definitions or overrides such as:

- `codex`
- `claude`
- future NightShift-native engine adapters

#### `skills/`

Skill-specific configuration such as:

- splitter presets
- prompt profiles
- context-loading rules

#### `plugins/`

Connector and integration metadata.

#### `cache/`

Rebuildable local caches.

#### `logs/`

Local CLI and adapter logs.

#### `state/`

Host-local non-project state such as:

- recent selections
- local indexes
- future session pointers

## Project Space

Project space is repository-scoped.

Recommended root:

`<repo>/.nightshift/`

This is the main operating surface for NightShift inside a repository.

## Two Project Categories

Project-space directories must be classified as either:

- versioned
- runtime-only

This distinction matters more than the exact directory names.

### Versioned

These files are part of the project's collaborative operating model and should live in git.

They include:

- project config
- execution work orders
- immutable contracts
- archived work orders
- optional policy documents

### Runtime-Only

These files are produced while NightShift runs and should not be committed in normal workflow.

They include:

- run history
- attempt artifacts
- transient reports
- temporary engine output

## Recommended Project Structure

```text
.nightshift/
  config/
  work-orders/
  contracts/
  records/
  archive/
  runs/
  artifacts/
  reports/
```

## Project Directory Meanings

### `config/`

Versioned project defaults.

Examples:

- repo execution defaults
- validation defaults
- issue or work-order defaults
- workflow policy

This is the project-level counterpart to `~/.nightshift/config/`.

### `work-orders/`

Versioned active execution work orders.

This is where the current execution branch should hold:

- `.nightshift/work-orders/WO-<id>.md`

These files are part of git history and are reviewed through draft PRs.

### `contracts/`

Versioned immutable contracts produced from approved work orders.

This is the long-term replacement direction for the current separate `nightshift/issues/*.yaml` model.

Contracts should remain stable runtime inputs, not editable planning documents.

### `records/`

Repository-scoped records that are useful to keep close to the project model.

This area is likely to evolve and may split further later.

In the near term, it can represent:

- current issue or work-order records
- ingestion linkage metadata
- delivery linkage summaries

Whether every record belongs in git should be decided per file type, not assumed globally.

### `archive/`

Versioned historical operating artifacts that should stay in the repo for traceability but should not clutter active paths.

Examples:

- merged execution work orders
- archived policy snapshots
- future summarized delivery manifests

Recommended work-order archive path:

- `.nightshift/archive/work-orders/YYYY/MM/WO-<id>.md`

### `runs/`

Runtime-only run history.

This holds:

- run state
- events
- attempt records
- run-scoped snapshots

This is the project-local successor shape for the current `nightshift-data/runs/` layout.

### `artifacts/`

Runtime-only attempt and delivery artifacts.

This includes:

- engine outputs
- stdout/stderr captures
- validation artifacts
- delivery staging artifacts

### `reports/`

Primarily runtime-only generated outputs.

Some reports may later be promoted into archiveable summaries, but generated run reports should not be assumed versioned by default.

## Execution Branch Relationship

An execution branch is a git concept, not a directory.

Each execution branch should contain:

- one primary active work order in `.nightshift/work-orders/`
- the implementation changes for that work order

The execution branch and its draft PR are the collaborative review surface.

## Work Order Placement Rule

Execution work orders should live inside project space, not in user space.

They are:

- project assets
- branch-scoped execution sources
- reviewable by collaborators

That makes `.nightshift/work-orders/` the correct default location.

## Contract Materialization Rule

NightShift should materialize immutable contracts from approved work orders into:

- `.nightshift/contracts/`

Work orders remain editable planning-and-execution artifacts.

Contracts remain fixed runtime artifacts.

Those roles must stay separate.

## Config Resolution Order

Recommended precedence:

1. CLI flags
2. project `.nightshift/config/`
3. user `~/.nightshift/config/`
4. built-in defaults

Secrets should not be embedded into versioned project config.

## Credential Rule

The default safe model should be:

- project config contains names, selectors, or provider references
- user space contains the corresponding credentials

This keeps repositories shareable without leaking operator secrets.

## Migration Direction From Current MVP Layout

This model does not require an immediate large migration.

The intended direction is:

- current `nightshift.yaml` evolves into project `.nightshift/config/`
- current `nightshift-data/` evolves into project `.nightshift/runs/`, `.nightshift/artifacts/`, and `.nightshift/reports/`
- current issue-contract storage evolves toward `.nightshift/contracts/`

The architecture matters more than immediate renaming.

## Relationship To Agent Evolution

This structure is intentionally compatible with a future where NightShift becomes a more self-contained agent operating environment.

That future may include:

- NightShift-native execution agents
- richer local skills
- stronger local state and indexing
- repo-local policy and context discovery

Those additions should fit into this model without changing the core boundary:

- user space for private operator context
- project space for repository operating context

## Deferred Questions

This document does not yet define:

- exact file names inside `config/`
- final record-file split within `records/`
- whether some reports should be promoted from runtime-only to archive
- the detailed migration path from current code and docs

Those should be resolved in follow-up implementation planning.
