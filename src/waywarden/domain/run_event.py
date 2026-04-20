"""RT-002 RunEvent envelope — frozen dataclass with payload validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Literal, cast, get_args

from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event_types import RunEventType

# ---------------------------------------------------------------------------
# Payload validation — required fields per event type (RT-002 §Event payload)
# ---------------------------------------------------------------------------

_REQUIRED_PAYLOAD_FIELDS: dict[str, frozenset[str]] = {
    "run.created": frozenset(
        ["instance_id", "profile", "policy_preset", "manifest_ref", "entrypoint"]
    ),
    "run.plan_ready": frozenset(
        ["plan_ref", "summary", "revision", "approval_required"]
    ),
    "run.execution_started": frozenset(
        ["worker_session_ref", "attempt", "resume_kind"]
    ),
    "run.progress": frozenset(["phase", "milestone"]),
    "run.approval_waiting": frozenset(
        ["approval_id", "approval_kind", "summary"]
    ),
    "run.resumed": frozenset(["resume_kind", "resumed_from_seq"]),
    "run.artifact_created": frozenset(
        ["artifact_ref", "artifact_kind", "label"]
    ),
    "run.completed": frozenset(["outcome"]),
    "run.failed": frozenset(["failure_code", "message", "retryable"]),
    "run.cancelled": frozenset(["reason"]),
}


def validate_payload(event_type: str, payload: Mapping[str, object]) -> None:
    """Enforce that *payload* contains every required field for *event_type*.

    Raises ``ValueError`` when a required field is missing.
    Extra keys in *payload* are accepted (forward compatibility).
    """
    if event_type not in _REQUIRED_PAYLOAD_FIELDS:
        raise ValueError(f"Unknown event type: {event_type!r}")

    required = _REQUIRED_PAYLOAD_FIELDS[event_type]
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(
            f"Event type {event_type!r} requires payload fields: "
            f"{', '.join(sorted(missing))}"
        )


# ---------------------------------------------------------------------------
# Causation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Causation:
    """Explanatory metadata linking this event to its cause.

    At least one of ``event_id``, ``action``, or ``request_id`` must be set.
    """

    event_id: str | None
    action: str | None
    request_id: str | None

    def __post_init__(self) -> None:
        if (
            self.event_id is None
            and self.action is None
            and self.request_id is None
        ):
            raise ValueError(
                "At least one of event_id, action, or request_id must be set"
            )


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------

_ActorKind = Literal["operator", "system", "scheduler", "worker", "policy-engine"]
_VALID_ACTOR_KINDS: frozenset[str] = frozenset(get_args(_ActorKind))


def _normalize_actor_kind(value: _ActorKind | str) -> _ActorKind:
    normalized = str(value)
    if normalized not in _VALID_ACTOR_KINDS:
        raise ValueError(
            "kind must be one of 'operator', 'system', 'scheduler', "
            "'worker', or 'policy-engine'"
        )
    return cast(_ActorKind, normalized)


@dataclass(frozen=True, slots=True)
class Actor:
    """Origin of a transition in provider-neutral terms."""

    kind: _ActorKind
    id: str | None
    display: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _normalize_actor_kind(self.kind))


# ---------------------------------------------------------------------------
# RunEvent envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunEvent:
    """Canonical RT-002 event envelope."""

    id: RunEventId
    run_id: RunId
    seq: int
    type: RunEventType
    payload: Mapping[str, object]
    timestamp: datetime
    causation: Causation | None
    actor: Actor | None

    def __post_init__(self) -> None:
        if not isinstance(self.seq, int) or self.seq < 1:
            raise ValueError("seq must be an integer >= 1")

        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
        # Normalise to UTC
        object.__setattr__(
            self, "timestamp", self.timestamp.astimezone(UTC)
        )

        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a Mapping[str, object]")
        frozen_payload = MappingProxyType(dict(self.payload))
        validate_payload(self.type, frozen_payload)
        object.__setattr__(self, "payload", frozen_payload)
