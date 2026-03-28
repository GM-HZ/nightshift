from enum import StrEnum


class IssueState(StrEnum):
    draft = "draft"
    ready = "ready"
    running = "running"
    blocked = "blocked"
    deferred = "deferred"
    done = "done"


class IssueKind(StrEnum):
    planning = "planning"
    repro = "repro"
    investigation = "investigation"
    execution = "execution"


class AttemptState(StrEnum):
    pending = "pending"
    preflight_failed = "preflight_failed"
    executing = "executing"
    validating = "validating"
    retryable = "retryable"
    accepted = "accepted"
    rejected = "rejected"
    aborted = "aborted"


class DeliveryState(StrEnum):
    none = "none"
    branch_ready = "branch_ready"
    pr_opened = "pr_opened"
    reviewed = "reviewed"
    merged = "merged"
    closed_without_merge = "closed_without_merge"


class RunState(StrEnum):
    initializing = "initializing"
    running = "running"
    stopping = "stopping"
    completed = "completed"
    aborted = "aborted"


class AlertSeverity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"
