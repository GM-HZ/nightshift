from nightshift.domain import IssueKind
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.product.delivery.github_pr import PullRequestPayload, render_pr_payload, render_pr_title
from nightshift.product.delivery.git_ops import render_commit_message


def _verification():
    return VerificationContract(
        issue_validation=VerificationStageContract(
            required=True,
            commands=("test -s README.zh-CN.md", 'rg -n "README\\.zh-CN\\.md|中文" README.md'),
            pass_condition=PassConditionContract(type="all_exit_codes_zero"),
        ),
        regression_validation=VerificationStageContract(
            required=True,
            commands=("test -s README.zh-CN.md",),
            pass_condition=PassConditionContract(type="all_exit_codes_zero"),
        ),
    )


def test_render_commit_message_uses_issue_id_and_title() -> None:
    message = render_commit_message(issue_id="GH-7", title="增加中文 README 说明", kind=IssueKind.execution)

    assert "GH-7" in message
    assert "增加中文 README 说明" in message


def test_render_pr_payload_contains_title_and_verification_commands() -> None:
    payload = render_pr_payload(
        repo_full_name="GM-HZ/nightshift",
        issue_id="GH-7",
        source_issue_ref="GM-HZ/nightshift#7",
        title="增加中文 README 说明",
        acceptance=("仓库根目录存在 README.zh-CN.md",),
        verification=_verification(),
    )

    assert isinstance(payload, PullRequestPayload)
    assert "GH-7" in payload.title
    assert "Verification" in payload.body
    assert "README.zh-CN.md" in payload.body
    assert "GM-HZ/nightshift#7" in payload.body


def test_render_pr_title_uses_issue_id_and_title() -> None:
    title = render_pr_title(issue_id="GH-7", issue_title="增加中文 README 说明")

    assert title == "GH-7: 增加中文 README 说明"
