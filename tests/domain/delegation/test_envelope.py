"""Unit tests for DelegationEnvelope value type."""

from __future__ import annotations

from typing import Any, cast

import pytest

from waywarden.domain.delegation.envelope import (
    DelegationEnvelope,
    make_envelope,
)
from waywarden.domain.ids import DelegationId, RunId


def test_envelope_is_frozen() -> None:
    """DelegationEnvelope is a frozen dataclass — no mutation."""
    from dataclasses import fields

    for f in fields(DelegationEnvelope):
        assert f.repr, f"field {f.name} should be repr'd"

    # frozen=True means no __setattr__
    env = DelegationEnvelope(
        id=DelegationId("del-001"),
        parent_run_id=RunId("run-001"),
        child_manifest=cast(Any, object()),
        brief="test",
        expected_outputs=["out"],
    )
    with pytest.raises((TypeError, Exception)):
        env_any = cast(Any, env)
        env_any.id = DelegationId("del-002")


def test_make_envelope() -> None:
    from waywarden.domain.ids import RunId

    env = make_envelope(
        parent_run_id=RunId("run-001"),
        child_manifest=cast(Any, object()),
        brief="sub task",
        expected_outputs=["summary"],
    )
    assert env.parent_run_id == RunId("run-001")
    assert env.brief == "sub task"
    assert env.expected_outputs == ["summary"]
