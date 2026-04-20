"""Tests for the RT-002 RunEvent envelope, Causation, Actor, and payload validation."""

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event import (
    Actor,
    Causation,
    RunEvent,
    validate_payload,
)


def test_envelope_field_names_match_spec() -> None:
    """Assert dataclass fields match the RT-002 envelope table verbatim."""
    expected_fields = {
        "id",
        "run_id",
        "seq",
        "type",
        "payload",
        "timestamp",
        "causation",
        "actor",
    }
    assert set(RunEvent.__dataclass_fields__.keys()) == expected_fields


def test_event_type_catalog_is_exact() -> None:
    """Assert typing.get_args(RunEventType) equals the 10-string frozenset."""
    from typing import get_args

    from waywarden.domain.run_event_types import RunEventType as _RunEventType

    expected = frozenset([
        "run.created",
        "run.plan_ready",
        "run.execution_started",
        "run.progress",
        "run.approval_waiting",
        "run.resumed",
        "run.artifact_created",
        "run.completed",
        "run.failed",
        "run.cancelled",
    ])
    assert set(get_args(_RunEventType)) == expected


def test_validate_payload_requires_fields_per_spec() -> None:
    """Parametrized check: every event type rejects missing required fields."""
    from typing import get_args

    from waywarden.domain.run_event_types import RunEventType as _RunEventType

    event_types = list(get_args(_RunEventType))

    for event_type in event_types:
        with pytest.raises(ValueError, match="requires payload fields"):
            validate_payload(event_type, {})

        # Partial payload — missing at least one required field
        with pytest.raises(ValueError, match="requires payload fields"):
            validate_payload(event_type, {"extra_key": "value"})


def test_validate_payload_accepts_extra_fields() -> None:
    """Extra keys in payload are accepted (forward compatibility)."""
    payload = {
        "instance_id": "i-1",
        "profile": "default",
        "policy_preset": "yolo",
        "manifest_ref": "m://v1",
        "entrypoint": "api",
        "unexpected_field": True,
    }
    validate_payload("run.created", payload)


def test_validate_payload_unknown_type() -> None:
    with pytest.raises(ValueError, match="Unknown event type"):
        validate_payload("run.custom_event", {})


def test_causation_requires_at_least_one_field() -> None:
    with pytest.raises(ValueError, match="At least one of"):
        Causation(event_id=None, action=None, request_id=None)

    # Each single-field variant should work
    Causation(event_id="evt-1", action=None, request_id=None)
    Causation(event_id=None, action="operator_resume", request_id=None)
    Causation(event_id=None, action=None, request_id="req-1")


def test_seq_must_be_positive() -> None:
    created_payload = MappingProxyType({
        "instance_id": "i-1",
        "profile": "default",
        "policy_preset": "yolo",
        "manifest_ref": "m://v1",
        "entrypoint": "api",
    })
    base = {
        "id": RunEventId("evt-1"),
        "run_id": RunId("run-1"),
        "type": "run.created",
        "payload": created_payload,
        "timestamp": datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
        "causation": None,
        "actor": None,
    }

    with pytest.raises(ValueError, match="seq must be an integer >= 1"):
        RunEvent(seq=0, **base)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="seq must be an integer >= 1"):
        RunEvent(seq=-1, **base)  # type: ignore[arg-type]

    # seq=1 is valid
    event = RunEvent(seq=1, **base)
    assert event.seq == 1


def test_timestamp_must_be_utc_aware() -> None:
    created_payload = MappingProxyType({
        "instance_id": "i-1",
        "profile": "default",
        "policy_preset": "yolo",
        "manifest_ref": "m://v1",
        "entrypoint": "api",
    })
    base = {
        "id": RunEventId("evt-1"),
        "run_id": RunId("run-1"),
        "seq": 1,
        "type": "run.created",
        "payload": created_payload,
        "causation": None,
        "actor": None,
    }

    with pytest.raises(ValueError, match="timezone-aware"):
        RunEvent(
            timestamp=datetime(2026, 4, 19, 14, 0),  # naive
            **base,
        )


def test_actor_kind_rejected_at_runtime() -> None:
    """Invalid Actor.kind raises ValueError at construction time."""
    with pytest.raises(ValueError, match="kind must be one of"):
        Actor(kind="invalid", id=None, display=None)  # type: ignore[arg-type]


def test_actor_kind_literal_accepted() -> None:
    """All valid Actor kinds pass at runtime."""
    Actor(kind="operator", id="user:marc", display="Marc")
    Actor(kind="system", id=None, display=None)
    Actor(kind="policy-engine", id=None, display="Policy")
    Actor(kind="scheduler", id=None, display=None)
    Actor(kind="worker", id=None, display=None)


def test_payload_frozen_at_construction() -> None:
    """RunEvent payload is immutable (MappingProxyType) after construction."""
    mutable_payload: dict[str, object] = {
        "instance_id": "i-1",
        "profile": "default",
        "policy_preset": "yolo",
        "manifest_ref": "m://v1",
        "entrypoint": "api",
    }
    event = RunEvent(
        id=RunEventId("evt-1"),
        run_id=RunId("run-1"),
        seq=1,
        type="run.created",
        payload=mutable_payload,
        timestamp=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
        causation=None,
        actor=None,
    )
    # Original mutable dict should still be unchanged
    assert "instance_id" in mutable_payload

    # Event payload should be frozen
    with pytest.raises(TypeError, match="item assignment"):
        event.payload["instance_id"] = "hacked"  # type: ignore[index]

    # Should be MappingProxyType
    assert isinstance(event.payload, MappingProxyType)


def test_run_event_rejects_missing_payload_fields() -> None:
    """RunEvent construction rejects payloads missing required fields for the event type."""
    with pytest.raises(ValueError, match="requires payload fields"):
        RunEvent(
            id=RunEventId("evt-1"),
            run_id=RunId("run-1"),
            seq=1,
            type="run.created",
            payload=MappingProxyType({"instance_id": "i-1"}),  # missing fields
            timestamp=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            causation=None,
            actor=None,
        )


def test_valid_run_event() -> None:
    payload = MappingProxyType({
        "instance_id": "i-1",
        "profile": "default",
        "policy_preset": "yolo",
        "manifest_ref": "m://v1",
        "entrypoint": "api",
    })
    event = RunEvent(
        id=RunEventId("evt-1"),
        run_id=RunId("run-1"),
        seq=1,
        type="run.created",
        payload=payload,
        timestamp=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
        causation=Causation(event_id=None, action="api_submit", request_id="req-1"),
        actor=Actor(kind="system", id=None, display=None),
    )
    assert event.seq == 1
    assert event.timestamp.tzinfo is not None
