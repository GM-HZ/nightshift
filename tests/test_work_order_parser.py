from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from nightshift.product.work_orders.models import WorkOrderFrontmatter
from nightshift.product.work_orders.parser import WorkOrderParseError, parse_work_order_markdown


def make_frontmatter_payload() -> dict[str, object]:
    return {
        "work_order_id": "WO-20260329-001",
        "status": "approved",
        "source_issue": {
            "repo": "GM-HZ/nightshift",
            "number": 7,
            "url": "https://github.com/GM-HZ/nightshift/issues/7",
        },
        "execution": {
            "title": "Add Chinese README",
            "goal": "Add a Chinese README and link it from the main README.",
            "allowed_paths": ["README.md", "README.zh-CN.md"],
            "non_goals": [
                "Change packaging",
                "Rewrite unrelated docs",
            ],
            "acceptance_criteria": [
                "README.zh-CN.md exists and is non-empty",
                "README.md links to README.zh-CN.md",
            ],
            "verification_commands": [
                "test -s README.zh-CN.md",
                "rg -n \"README\\\\.zh-CN\\\\.md\" README.md",
            ],
            "context_files": ["README.md"],
        },
        "rationale": {
            "summary": "Add a Chinese entry point without expanding scope into a full docs rewrite.",
            "risks": [
                "Terminology drift from existing product docs",
            ],
            "notes": [
                "Follow current README tone and structure",
            ],
        },
    }


def test_work_order_frontmatter_accepts_minimal_required_structure() -> None:
    payload = make_frontmatter_payload()

    frontmatter = WorkOrderFrontmatter.model_validate(payload)

    assert frontmatter.work_order_id == "WO-20260329-001"
    assert frontmatter.execution.title == "Add Chinese README"
    assert frontmatter.execution.verification_commands == (
        "test -s README.zh-CN.md",
        "rg -n \"README\\\\.zh-CN\\\\.md\" README.md",
    )
    assert frontmatter.execution.issue_id is None
    assert frontmatter.execution.verification is None
    assert frontmatter.execution.priority is None
    assert frontmatter.execution.engine_hints is None
    assert frontmatter.rationale.summary.startswith("Add a Chinese entry point")


def test_work_order_frontmatter_accepts_structured_verification_shape() -> None:
    payload = make_frontmatter_payload()
    payload["execution"] = {
        "title": "Add Chinese README",
        "goal": "Add a Chinese README and link it from the main README.",
        "allowed_paths": ["README.md", "README.zh-CN.md"],
        "non_goals": [
            "Change packaging",
            "Rewrite unrelated docs",
        ],
        "acceptance_criteria": [
            "README.zh-CN.md exists and is non-empty",
            "README.md links to README.zh-CN.md",
        ],
        "verification": {
            "issue_validation": ["test -s README.zh-CN.md"],
            "regression_validation": ["rg -n \"README\\\\.zh-CN\\\\.md\" README.md"],
            "promotion_validation": [],
        },
        "context_files": ["README.md"],
    }
    payload["execution"]["issue_id"] = "ISSUE-7"

    frontmatter = WorkOrderFrontmatter.model_validate(payload)

    assert frontmatter.execution.verification_commands is None
    assert frontmatter.execution.verification is not None
    assert frontmatter.execution.verification.issue_validation == ("test -s README.zh-CN.md",)
    assert frontmatter.execution.verification.regression_validation == (
        "rg -n \"README\\\\.zh-CN\\\\.md\" README.md",
    )
    assert frontmatter.execution.issue_id == "ISSUE-7"


@pytest.mark.parametrize(
    "missing_field",
    ["goal", "allowed_paths", "non_goals", "acceptance_criteria", "context_files"],
)
def test_work_order_execution_rejects_missing_required_fields(missing_field: str) -> None:
    payload = make_frontmatter_payload()
    execution = deepcopy(payload["execution"])
    assert isinstance(execution, dict)
    execution.pop(missing_field)
    payload["execution"] = execution

    with pytest.raises(ValidationError):
        WorkOrderFrontmatter.model_validate(payload)


def test_work_order_execution_requires_verification_input() -> None:
    payload = make_frontmatter_payload()
    execution = deepcopy(payload["execution"])
    assert isinstance(execution, dict)
    execution.pop("verification_commands")
    payload["execution"] = execution

    with pytest.raises(ValidationError):
        WorkOrderFrontmatter.model_validate(payload)


def test_work_order_frontmatter_rejects_body_prose_as_frontmatter() -> None:
    payload = make_frontmatter_payload()
    payload["body"] = "The body can mention a goal, but it is not frontmatter."

    with pytest.raises(ValidationError, match="body"):
        WorkOrderFrontmatter.model_validate(payload)


def test_parse_work_order_markdown_extracts_frontmatter_and_body() -> None:
    markdown = """---
work_order_id: WO-20260329-001
status: approved
source_issue:
  repo: GM-HZ/nightshift
  number: 7
execution:
  title: Add Chinese README
  goal: Add a Chinese README and link it from the main README.
  allowed_paths:
    - README.md
    - README.zh-CN.md
  non_goals:
    - Change packaging
    - Rewrite unrelated docs
  acceptance_criteria:
    - README.zh-CN.md exists and is non-empty
    - README.md links to README.zh-CN.md
  verification_commands:
    - test -s README.zh-CN.md
  context_files:
    - README.md
rationale:
  summary: Add a Chinese entry point without expanding scope into a full docs rewrite.
---

# Execution Work Order

## Background

Human-readable notes stay in the body.
"""

    parsed = parse_work_order_markdown(markdown)

    assert parsed.frontmatter.work_order_id == "WO-20260329-001"
    assert parsed.frontmatter.execution.title == "Add Chinese README"
    assert parsed.frontmatter.execution.verification_commands == ("test -s README.zh-CN.md",)
    assert parsed.body == "\n# Execution Work Order\n\n## Background\n\nHuman-readable notes stay in the body.\n"


def test_parse_work_order_markdown_rejects_missing_frontmatter() -> None:
    markdown = "# Execution Work Order\n\nThis file has no frontmatter."

    with pytest.raises(WorkOrderParseError, match="frontmatter"):
        parse_work_order_markdown(markdown)


def test_parse_work_order_markdown_rejects_malformed_yaml() -> None:
    markdown = """---
work_order_id: WO-20260329-001
status: approved
source_issue:
  repo: GM-HZ/nightshift
  number: 7
execution:
  title: Add Chinese README
  goal Add a Chinese README and link it from the main README.
  allowed_paths:
    - README.md
    - README.zh-CN.md
  non_goals:
    - Change packaging
  acceptance_criteria:
    - README.zh-CN.md exists and is non-empty
  verification_commands:
    - test -s README.zh-CN.md
  context_files:
    - README.md
rationale:
  summary: Add a Chinese entry point without expanding scope into a full docs rewrite.
---
"""

    with pytest.raises(WorkOrderParseError, match="YAML"):
        parse_work_order_markdown(markdown)
