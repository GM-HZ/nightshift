# Notifications And Alerts MVP

## Purpose

This document defines the smallest alerting layer that fits the current NightShift repository state after:

- GitHub issue ingestion bridge
- execution work order materialization
- queue admission
- batch run
- overnight control loop MVP
- explicit delivery

It is intentionally smaller than a full notification platform.

The goal is to add a governed operator-alert surface without coupling it too tightly to:

- rich reports
- post-PR workflow
- advanced scheduling
- multi-provider delivery policy

---

## Current Baseline

NightShift already has:

- `AlertEvent` in the domain model
- append-only alert persistence in `StateStore`
- `alerts` config fields for enabled channels and severity thresholds
- run state support for `alert_counts`

What it does not have yet:

- alert policy generation
- notification dispatch
- operator delivery channels

So the missing layer is not storage. It is alert production and dispatch.

---

## Alignment With `v4.2.1`

This MVP stays aligned with `v4.2.1` because:

- alerts remain normalized product-side events
- persistence remains append-only
- the kernel does not become channel-aware
- notification delivery remains an edge module above durable alert recording

This is a product-side operator escalation layer, not a kernel redesign.

---

## Design Principle

Alerts and notifications should be split into two steps:

1. **Alert creation**
   NightShift decides that an operator-visible event happened and writes a durable `AlertEvent`.
2. **Notification dispatch**
   NightShift attempts to fan that alert out to one or more configured channels.

The durable alert record is the source of truth.

Channel dispatch is secondary and may fail independently.

This keeps alert history trustworthy even when notification delivery is unreliable.

---

## MVP Scope

### In Scope

- alert policy for the most important overnight-loop and delivery failures
- durable alert recording
- channel dispatcher abstraction
- one conservative first delivery channel set
- loop-level alert counts

### Out Of Scope

- notification batching and digesting
- provider-specific formatting beyond a small common shape
- escalation routing trees
- alert deduplication windows across long periods
- rich UI or inbox
- merge/review policy alerts

---

## Alert Sources In MVP

The MVP should generate alerts for these cases:

### Overnight Loop

- daemon loop aborted on failure
- stop requested while loop is running
- no active daemon run when `stop` is called is **not** an alert; it is a CLI usage error

### Execution

- repeated engine crashes in the same controlling run
- recovery failure
- state-store corruption or unreadable metadata

### Delivery

- explicit delivery failure after an issue is already accepted

### Global

- total overnight timeout reached

The loop does not need to alert on every accepted issue.

---

## Severity Model

The MVP should use only the existing severities:

- `info`
- `warning`
- `critical`

Suggested mapping:

- `info`
  - daemon stop requested
  - daemon drained normally, if operators want completion notices later

- `warning`
  - delivery failure for a single accepted issue
  - repeated engine crash threshold crossed for one run

- `critical`
  - daemon aborted unexpectedly
  - recovery failure
  - total overnight timeout
  - state-store corruption or unreadable runtime metadata

---

## Durable Alert Record

The authoritative object remains `AlertEvent`.

MVP alert creation should populate:

- `alert_id`
- `run_id`
- `issue_id` when applicable
- `severity`
- `event_type`
- `summary`
- `details`
- `created_at`
- `delivery_status`

Suggested `delivery_status` values for the MVP:

- `pending`
- `delivered`
- `failed`
- `skipped`

The record should be appended before any channel dispatch attempt.

---

## Dispatch Model

The dispatcher should work like this:

1. create and persist alert
2. resolve enabled channels from config
3. send the alert to each enabled channel
4. update in-memory delivery result for the current command path
5. do not rewrite historical alert records in place

This means `delivery_status` in the durable record is the initial dispatcher result for that emission attempt, not a mutable forever-updated state machine.

That is acceptable for MVP.

---

## First Channel Set

The MVP should implement only these channels:

- `console`
- `webhook`

### `console`

Use for:

- foreground commands
- local debugging
- immediate operator visibility when NightShift is run interactively

### `webhook`

Use for:

- unattended overnight execution
- generic integration with external systems

This keeps the first notification surface small while still providing a real unattended channel.

Channels such as Slack, email, or GitHub-native comments can come later on top of the same dispatcher contract.

---

## Config Direction

This MVP should continue to use the existing `alerts` config section, but with clearer semantics.

Project-level config:

- `alerts.enabled_channels`
- `alerts.severity_thresholds`

User-level config should later provide channel credentials or endpoints under `~/.nightshift/`.

For MVP, a simple bridge is enough:

- channel selection remains in project config
- webhook endpoint or channel-specific settings can be resolved from user space

This keeps secrets out of repo config.

---

## Integration Points

### Overnight Loop

The overnight loop service is the highest-value first integration point.

It should emit alerts when:

- the loop aborts on failure
- a stop request is observed
- a total overnight timeout is exceeded later

### Delivery

The explicit delivery service should emit alerts when:

- an accepted issue cannot be pushed
- a PR cannot be created

### Recovery

Recovery should emit alerts when:

- metadata or state cannot be reconstructed safely
- recovery orchestration itself fails

---

## Run State Relationship

`RunState.alert_counts` should be updated during the current run when alerts are emitted.

This count is:

- a summary convenience for report and operator views
- not the source of truth

The append-only alert log remains authoritative.

---

## Why This MVP Is The Right Size

This is the smallest useful alerting layer because it:

- reuses the domain model already present
- keeps durable alert history primary
- introduces a clear dispatcher seam
- gives the overnight loop a real operator-escalation path
- avoids prematurely designing a full notification platform

It is enough to move NightShift from “can run unattended” toward “can run unattended and tell someone when it matters.”

---

## Follow-On Work

After this MVP is stable, the next natural expansions are:

1. richer alert policy tuning
2. digest and summary notifications
3. notification delivery retries
4. richer morning report integration
5. provider-specific adapters beyond webhook
