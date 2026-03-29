# NightShift Current Capability Truth Matrix

## Purpose

This document is the shortest "what the repository actually supports today" view.

It is intentionally narrower than the `v4.2.1` coverage matrix.

Use it when documentation and code seem to disagree.

The rule is simple:

- this file follows the live codebase
- it does not describe planned product behavior unless that behavior is present in code

---

## 1. Current CLI Surface

The live CLI currently exposes these commands:

- `issue ingest-github`
- `run --issues`
- `run --all`
- `run-one`
- `recover`
- `report`
- `queue status`
- `queue show`
- `queue add`
- `queue reprioritize`

Notes:

- there is no live `split` command
- there is no live `proposals` command group
- there is no live `deliver --issues`

Practical consequence:

- the current operator surface is still narrower than the full `v4.2.1` product direction
- but GitHub issue ingestion bridge and product-facing batch execution are now live

---

## 2. Current Kernel Capabilities

These capabilities are present in code and verified by tests:

- immutable `IssueContract`
- mutable `IssueRecord`
- `AttemptRecord` and `RunState` persistence split
- current-state versus run-history truth split
- single-issue execution via `run-one`
- validation-gated acceptance and rejection
- rollback on failure
- isolated worktree execution
- rerun-safe worktree reuse
- recovery into a new controlling run
- minimal historical report
- Codex and Claude adapters
- runtime storage and contract storage resolvers

This remains the strongest and most complete part of the repository.

---

## 3. Current Product-Layer Capabilities In Code

Only these product-side capabilities are currently present in code:

- GitHub issue ingestion bridge
- queue admission service
- execution work order parser
- execution work order materialization
- queue-time contract freeze
- frozen work order provenance on `IssueContract`
- product-facing batch execution commands
- contract context field preservation:
  - `non_goals`
  - `context_files`

Notes:

- these capabilities are real and active
- they support the newer execution-work-order design direction
- they do not yet imply a full product workflow surface

---

## 4. Product Capabilities That Are Not Present In Live Code

These were previously described in design docs or historical implementation notes, but are not present in the current code tree:

- splitter CLI
- proposal persistence and proposal review CLI
- delivery / PR dispatcher CLI
- notification adapters
- rich report generator
- unattended overnight daemon loop

Practical consequence:

- these should currently be treated as design direction, not live repository capability

---

## 5. Current `.nightshift` Migration Status

The repository now supports these migration-related capabilities:

- layered project config resolution
- layered contract storage resolution
- layered runtime storage resolution
- compatibility mode remains supported

Supported markers include:

- `project_config_source`
- `contract_storage_source`
- `runtime_layout_source`

What this means in practice:

- the repository is already moving toward the `.nightshift/` model
- but the migration is still phased and compatibility-first
- user-space `~/.nightshift/` adoption is still a design direction, not a completed implementation

---

## 6. What Is Most Important To Fix In Documentation

If docs are updated after reading this file, the highest-priority corrections are:

- do not claim that splitter / ingestion / delivery CLI is currently live unless it is reintroduced into code
- do not present the full product chain as a current operator flow
- distinguish clearly between:
  - live kernel and queue-admission behavior
  - design-forward product workflow documents
- keep `.nightshift` migration language aligned with the current phased rollout

---

## 7. Bottom Line

The current repository state is best described as:

- kernel: live and strong
- queue admission plus work order materialization: live
- broader product workflow: mostly design direction, not current live code surface

This is the file to trust first when deciding whether a capability exists now or is still planned.
