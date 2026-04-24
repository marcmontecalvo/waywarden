"""ask preset — must gate write and exec operations."""

import pytest

from waywarden.policy.loader import PolicyLoader


@pytest.fixture()
def ask_policy() -> PolicyLoader:
    return PolicyLoader()


def test_ask_gates_write_and_exec(ask_policy: PolicyLoader) -> None:
    """ask must gate shell.write, http.post, and tool.exec by default."""
    policy = ask_policy.load("ask")

    shell_write = [r for r in policy.rules if r.tool == "shell" and r.action == "write"]
    http_post = [r for r in policy.rules if r.tool == "http" and r.action == "post"]
    shell_exec = [r for r in policy.rules if r.tool == "shell" and r.action == "exec"]

    for rule in shell_write + http_post + shell_exec:
        assert rule.decision == "approval-required", (
            f"Rule for {rule.tool}.{rule.action} in ask preset "
            f"must be 'approval-required', got '{rule.decision}'"
        )
        assert rule.reason is not None, (
            f"Gated rule for {rule.tool}.{rule.action} must include a reason"
        )


def test_ask_default_decision_is_approval_required(ask_policy: PolicyLoader) -> None:
    """ask must have default_decision = 'approval-required'."""
    policy = ask_policy.load("ask")
    assert policy.default_decision == "approval-required"
