# Overnight Control Loop MVP Implementation Plan

## Goal

Implement the smallest unattended overnight control layer that fits the current live NightShift repository surface.

This plan follows:

- `docs/architecture/product/overnight-control-loop-mvp.md`
- the current live `run --all` and `run-one` behavior
- the current `.nightshift` migration model

It intentionally does not include:

- notifications
- rich reports
- parallel or slot-aware scheduling
- continue-on-failure
- automatic delivery coupling

---

## Task 1: Loop Metadata Model

Add a small persisted loop-metadata model for daemon runs.

Scope:

- define daemon loop metadata schema
- persist it under the run directory
- support:
  - `loop_mode`
  - `fail_fast`
  - `stop_requested`
  - `stopped_reason`

Done when:

- a daemon run can persist and reload loop metadata without changing kernel run-state semantics

---

## Task 2: Loop State Store Helpers

Add the storage helpers needed to manage daemon loop metadata and active daemon identity.

Scope:

- save/load daemon loop metadata
- resolve active daemon run for a repository
- keep compatibility with existing runtime storage resolver

Done when:

- the product layer can query and update daemon loop metadata without hardcoding paths

---

## Task 3: Daemon Loop Service

Implement the MVP overnight loop service above the current batch-run surface.

Scope:

- create controlling daemon run
- repeatedly select schedulable issues
- call existing `RunOrchestrator.run_one()`
- stop on:
  - no schedulable issues
  - first failure
  - explicit stop request
- append loop-level events

Done when:

- daemon execution works sequentially and fail-fast using current live queue semantics

---

## Task 4: CLI Surface

Extend the CLI with the MVP daemon controls.

Scope:

- `nightshift run --all --daemon`
- `nightshift stop`
- reject unsupported flag combinations cleanly
- print operator-friendly summaries and run ids

Done when:

- an operator can start and stop an unattended daemon run from the CLI

---

## Task 5: Recovery And Report Alignment

Ensure daemon loop metadata does not conflict with existing recovery and report flows.

Scope:

- preserve current `recover --run` semantics
- ensure report can still read the controlling run cleanly
- make failure and stop summaries point operators to the right persisted state

Done when:

- daemon runs remain compatible with existing recovery and report behavior

---

## Task 6: Documentation Sync

Update operator and product docs to reflect the new live daemon surface.

Scope:

- `README.md`
- `docs/usage/workflow.md`
- truth matrix
- backlog or product design entry where needed

Done when:

- docs describe daemon loop conservatively and consistently with code

---

## Task 7: Final Verification

Run targeted and full verification before claiming completion.

Minimum expected verification:

- daemon loop tests
- CLI tests
- state-store tests affected by new metadata
- full repository test suite

Done when:

- targeted coverage passes
- full suite passes

---

## Recommended Execution Order

1. loop metadata model
2. loop state store helpers
3. daemon loop service
4. CLI surface
5. recovery/report alignment
6. docs sync
7. final verification

---

## Notes

This plan deliberately treats the overnight control loop as a product-side wrapper around the current live kernel.

It should not:

- replace `run-one`
- change queue admission semantics
- change contract freeze semantics
- introduce a second scheduler

The point is to restore an unattended overnight layer while keeping the current system stable.
