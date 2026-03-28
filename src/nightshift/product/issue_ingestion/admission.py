from __future__ import annotations

from nightshift.config.models import NightShiftConfig

from .models import AdmissionCheckResult, AdmittedIssueDraft, ParsedIssueTemplate


def check_issue_admission(parsed: ParsedIssueTemplate, config: NightShiftConfig) -> AdmissionCheckResult:
    reasons: list[str] = []

    if not parsed.goal:
        reasons.append("Goal section is required")
    if not parsed.allowed_paths:
        reasons.append("Allowed Paths section must contain at least one path")
    if not parsed.acceptance_criteria:
        reasons.append("Acceptance Criteria section must contain at least one item")
    if not parsed.verification_commands:
        reasons.append("Verification Commands section must contain at least one command")

    if reasons:
        return AdmissionCheckResult(accepted=False, reasons=tuple(reasons))

    draft = AdmittedIssueDraft(
        issue_id=f"GH-{parsed.issue_number}",
        repo_full_name=parsed.repo_full_name,
        source_issue_number=parsed.issue_number,
        title=parsed.title,
        description=parsed.background,
        goal=parsed.goal,
        allowed_paths=parsed.allowed_paths,
        forbidden_paths=tuple(config.issue_defaults.default_forbidden_paths),
        acceptance_criteria=parsed.acceptance_criteria,
        verification_commands=parsed.verification_commands,
        priority=config.issue_defaults.default_priority,
        notes=parsed.notes,
    )
    return AdmissionCheckResult(accepted=True, draft=draft)
