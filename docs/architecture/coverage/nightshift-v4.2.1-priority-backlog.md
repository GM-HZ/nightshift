# NightShift V4.2.1 Priority Backlog

## Purpose

This document turns the remaining `v4.2.1` gaps into a practical backlog.

It is intentionally priority-first.

Use it to answer:

- what should be built next
- what is important but not blocking
- what should wait until the product loop is more complete

This backlog assumes the current repository baseline is:

- kernel: implemented
- GitHub issue ingestion bridge: implemented
- queue admission and execution work order materialization: implemented
- product-facing batch run surface: implemented
- conservative explicit delivery surface: implemented
- `.nightshift` migration phases 1-3: implemented

---

## Priority 1: Must Build Next

These items are the shortest path from the current repository state to a fuller NightShift product loop.

### 1. Planning Entry Surface

Current gap:

- live code does not currently expose:
  - `split`
  - `proposals`

Why it matters:

- the current live system now has a GitHub issue bridge
- but richer planning entry above that bridge is still missing

What “done” means:

- richer planning intake exists again in live code
- proposal review is no longer only a design artifact
- execution-facing inputs can enter the system without bypassing the product surface

### 2. Delivery Closure

Current gap:

- delivery closure is now back in live code as an explicit conservative path
- but richer delivery policy and stronger accepted-result freezing are still incomplete

Why it matters:

- the product loop is now present, but it still needs stronger guarantees and better delivery policy
- without stronger freezing semantics, delivery remains vulnerable to post-acceptance drift

What “done” means:

- NightShift can take an accepted execution result and deliver it through a governed PR path
- the delivered content is tied to a frozen accepted result, not just the current worktree

### 3. User-Space Operator Environment

Current gap:

- project-side `.nightshift` migration has started
- a first user-side `~/.nightshift/` layer is now live for:
  - `config/user.yaml`
  - `auth/github.yaml`
- broader user-space config/auth/profile structure is still not complete

Why it matters:

- long-lived operator usability depends on user-level config and auth
- current environment handling is still closer to repo-local engineering configuration than a real operator tool

What “done” means:

- user-level config exists
- auth/token management has a defined live home
- engine/profile defaults can be configured outside a single repo

---

## Priority 2: Next-Stage Product Depth

These items matter for unattended nighttime operation, but they do not block the immediate product loop closure.

### 4. Overnight Control Loop

Current gap:

- no unattended daemon loop
- no stop / pause / resume control
- no continue-on-failure behavior
- no dependency-aware or slot-aware scheduling

Why it matters:

- current `run --issues` and `run --all` are useful, but still operator-invoked batch commands
- true overnight operation needs a stronger control layer

What “done” means:

- NightShift can govern a multi-issue unattended execution window
- control behavior is explicit and observable

### 5. Notifications And Alerts

Current gap:

- no notification adapter
- no operator delivery channels for alerts

Why it matters:

- unattended systems need escalation paths when something important goes wrong

What “done” means:

- NightShift can surface meaningful events to operators through explicit channels

### 6. Rich Report Generator

Current gap:

- current report output is still minimal and historical
- no richer operator report layer
- no cross-run comparison

Why it matters:

- overnight operation needs a better morning handoff than raw minimal JSON alone

What “done” means:

- operators can review useful run summaries without reconstructing state manually

---

## Priority 3: Can Wait Until After Loop Closure

These items are valuable, but should not outrank the core product loop and operator model.

### 7. Richer Splitter Quality

Current gap:

- decomposition quality is still intentionally thin in the design direction

Why it can wait:

- getting the product loop live matters more than making the planning generator sophisticated immediately

### 8. Proposal Review UX Improvements

Current gap:

- review experience is still conceptually CLI/file-oriented in the design direction

Why it can wait:

- the main need is for the planning path to exist again in live code
- richer ergonomics can follow once that surface is restored

### 9. Post-PR Workflow Policy

Current gap:

- no merge automation
- no review-thread sync
- no PR reopen/update policy
- no reviewer / label policy

Why it can wait:

- these improve release-management maturity
- they do not need to come before planning-entry and delivery closure

---

## Recommended Build Order

The recommended implementation order from the current baseline is:

1. planning entry surface
2. delivery closure
3. `~/.nightshift/` user-space config and auth
4. overnight control loop
5. notifications and rich reporting
6. post-PR workflow policy and richer planning ergonomics

---

## Bottom Line

NightShift is now past the stage of proving that the kernel can work.

The next phase is about turning the current:

- queue admission
- frozen contracts
- batch run

into a more complete product loop:

`planning -> admission -> execution -> delivery -> operator review`

This backlog is the current recommended path to get there.
