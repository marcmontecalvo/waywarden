"""allowlist preset — default_decision must be 'forbidden'."""

import pytest

from waywarden.policy.loader import PolicyLoader


@pytest.fixture()
def allowlist_policy() -> PolicyLoader:
    return PolicyLoader()


def test_allowlist_default_decision_is_forbidden(allowlist_policy: PolicyLoader) -> None:
    """allowlist must have default_decision = 'forbidden'."""
    policy = allowlist_policy.load("allowlist")
    assert policy.default_decision == "forbidden"

    # Most rules should be explicitly allowed (allowlist pattern)
    auto_allowed = [r for r in policy.rules if r.decision == "auto-allow"]
    assert len(auto_allowed) < len(policy.rules), (
        "allowlist should have some allowed rules but not everything allowed"
    )
