"""yolo preset — must explicitly forbid at least two dangerous capabilities."""

import pytest

from waywarden.policy.loader import PolicyLoader


@pytest.fixture()
def yolo_policy() -> PolicyLoader:
    return PolicyLoader()


def test_yolo_has_hard_denials(yolo_policy: PolicyLoader) -> None:
    """yolo must explicitly forbid at least two capabilities."""
    policy = yolo_policy.load("yolo")

    forbidden_tools = [r for r in policy.rules if r.decision == "forbidden"]
    assert len(forbidden_tools) >= 2, (
        f"yolo preset must forbid at least 2 capabilities, "
        f"but only {len(forbidden_tools)} are forbidden"
    )
    for rule in forbidden_tools:
        assert rule.reason is not None, (
            f"Forbidden rule for tool '{rule.tool}' must include a reason"
        )


def test_yolo_default_decision_is_auto_allow(yolo_policy: PolicyLoader) -> None:
    """yolo must have default_decision = 'auto-allow'."""
    policy = yolo_policy.load("yolo")
    assert policy.default_decision == "auto-allow"


def test_yolo_at_least_one_rule_not_default(yolo_policy: PolicyLoader) -> None:
    """yolo must have explicit rules (not rely solely on default)."""
    policy = yolo_policy.load("yolo")
    assert len(policy.rules) > 0, "yolo should have explicit rules listed"
