from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nightshift.config.models import NightShiftConfig
from nightshift.domain import AttemptState, DeliveryState, IssueKind, IssueState
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.records import IssueRecord
from nightshift.registry.issue_registry import IssueRegistry

from .models import AdmittedIssueDraft


def materialize_issue(
    repo_root: str | Path,
    draft: AdmittedIssueDraft,
    config: NightShiftConfig,
    *,
    queue_admitted: bool = True,
) -> tuple[IssueContract, IssueRecord]:
    registry = IssueRegistry(repo_root)
    contract = _build_contract(draft, config)
    record = _build_record(contract, queue_admitted=queue_admitted)
    registry.save_contract(contract)
    registry.save_record(record)
    return contract, record


def _build_contract(draft: AdmittedIssueDraft, config: NightShiftConfig) -> IssueContract:
    return IssueContract(
        issue_id=draft.issue_id,
        title=draft.title,
        kind=IssueKind.execution,
        goal=draft.goal,
        description=draft.description,
        allowed_paths=draft.allowed_paths,
        forbidden_paths=draft.forbidden_paths,
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=draft.verification_commands,
                pass_condition=PassConditionContract(type="all_exit_codes_zero"),
            ),
            regression_validation=VerificationStageContract(
                required=True,
                commands=draft.verification_commands,
                pass_condition=PassConditionContract(type="all_exit_codes_zero"),
            ),
        ),
        test_edit_policy=TestEditPolicyContract.model_validate(
            config.issue_defaults.default_test_edit_policy.model_dump(mode="json")
        ),
        attempt_limits=AttemptLimitsContract.model_validate(
            config.issue_defaults.default_attempt_limits.model_dump(mode="json")
        ),
        timeouts=TimeoutsContract.model_validate(config.issue_defaults.default_timeouts.model_dump(mode="json")),
        priority=draft.priority,
        acceptance=draft.acceptance_criteria,
        notes=draft.notes,
    )


def _build_record(contract: IssueContract, *, queue_admitted: bool) -> IssueRecord:
    now = datetime.now(timezone.utc)
    return IssueRecord.from_contract(
        contract,
        issue_state=IssueState.ready if queue_admitted else IssueState.draft,
        attempt_state=AttemptState.pending,
        delivery_state=DeliveryState.none,
        created_at=now,
        updated_at=now,
    )
