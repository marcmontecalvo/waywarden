"""custom preset — must be loadable as a working template."""

import pytest

from waywarden.policy.loader import PolicyLoader


@pytest.fixture()
def custom_policy() -> PolicyLoader:
    return PolicyLoader()


def test_custom_is_loadable_template(custom_policy: PolicyLoader) -> None:
    """custom must parse and produce a policy with at least one rule."""
    policy = custom_policy.load("custom")
    assert policy.preset == "custom"  # type: ignore[comparison-overlap]
    assert len(policy.rules) >= 1, "custom template must have at least one rule"
    # Verify the rule has required fields
    rule = policy.rules[0]
    assert rule.tool is not None
    assert rule.decision is not None
    assert rule.reason is not None


def test_custom_default_decision_is_approval_required(custom_policy: PolicyLoader) -> None:
    """custom defaults to approval-required as a sensible template."""
    policy = custom_policy.load("custom")
    assert policy.default_decision == "approval-required"
