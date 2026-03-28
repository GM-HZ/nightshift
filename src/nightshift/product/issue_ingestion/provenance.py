from __future__ import annotations

from nightshift.config.models import NightShiftConfig

from .models import ParsedIssueTemplate, ProvenanceCheckResult


def check_issue_provenance(parsed: ParsedIssueTemplate, config: NightShiftConfig) -> ProvenanceCheckResult:
    reasons: list[str] = []
    settings = config.product.issue_ingestion

    if not settings.enabled:
        reasons.append("issue ingestion is disabled in product.issue_ingestion.enabled")

    if parsed.author_login not in settings.allowed_authors:
        reasons.append(f"author {parsed.author_login} is not allowlisted")

    if settings.required_label not in parsed.labels:
        reasons.append(f"required label {settings.required_label} is missing")

    if not parsed.nightshift_issue:
        reasons.append("NightShift-Issue marker must be true")

    if not parsed.nightshift_version:
        reasons.append("NightShift-Version marker is missing")

    return ProvenanceCheckResult(accepted=not reasons, reasons=tuple(reasons))
