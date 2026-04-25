"""RT-002 Run domain model — frozen dataclass aligned to the canonical run lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast, get_args

from waywarden.domain.ids import InstanceId, RunId, TaskId

RunState = Literal[
    "created",
    "planning",
    "executing",
    "waiting_approval",
    "completed",
    "failed",
    "cancelled",
]
_VALID_STATES: frozenset[str] = frozenset(get_args(RunState))

_PolicyPreset = Literal["yolo", "ask", "allowlist", "custom"]
_VALID_POLICY_PRESETS: frozenset[str] = frozenset(["yolo", "ask", "allowlist", "custom"])

_Entrypoint = Literal["api", "cli", "scheduler", "internal"]
_VALID_ENTRYPOINTS: frozenset[str] = frozenset(["api", "cli", "scheduler", "internal"])


def _require_non_empty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} must not be blank")
    return trimmed


def _require_aware_datetime(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _normalize_state(value: RunState | str) -> RunState:
    normalized = _require_non_empty_text(value, field_name="state")
    if normalized not in _VALID_STATES:
        raise ValueError(
            "state must be one of 'created', 'planning', 'executing', "
            "'waiting_approval', 'completed', 'failed', or 'cancelled'"
        )
    return cast(RunState, normalized)


def _normalize_policy_preset(value: _PolicyPreset | str) -> _PolicyPreset:
    normalized = _require_non_empty_text(value, field_name="policy_preset")
    if normalized not in _VALID_POLICY_PRESETS:
        raise ValueError("policy_preset must be one of 'yolo', 'ask', 'allowlist', or 'custom'")
    return cast(_PolicyPreset, normalized)


def _normalize_entrypoint(value: _Entrypoint | str) -> _Entrypoint:
    normalized = _require_non_empty_text(value, field_name="entrypoint")
    if normalized not in _VALID_ENTRYPOINTS:
        raise ValueError("entrypoint must be one of 'api', 'cli', 'scheduler', or 'internal'")
    return cast(_Entrypoint, normalized)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class Run:
    """Immutable run record aligned to the RT-002 run lifecycle."""

    id: RunId
    instance_id: InstanceId
    task_id: TaskId | None
    profile: str
    policy_preset: _PolicyPreset
    manifest_ref: str
    entrypoint: _Entrypoint
    state: RunState
    created_at: datetime
    updated_at: datetime
    terminal_seq: int | None
    manifest_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            RunId(_require_non_empty_text(self.id, field_name="id")),
        )
        object.__setattr__(
            self,
            "instance_id",
            InstanceId(_require_non_empty_text(self.instance_id, field_name="instance_id")),
        )
        if self.task_id is not None:
            from waywarden.domain.ids import TaskId as _TaskId

            object.__setattr__(
                self,
                "task_id",
                _TaskId(_require_non_empty_text(self.task_id, field_name="task_id")),
            )
        object.__setattr__(
            self,
            "profile",
            _require_non_empty_text(self.profile, field_name="profile"),
        )
        object.__setattr__(
            self,
            "policy_preset",
            _normalize_policy_preset(self.policy_preset),
        )
        object.__setattr__(
            self,
            "manifest_ref",
            _require_non_empty_text(self.manifest_ref, field_name="manifest_ref"),
        )
        object.__setattr__(
            self,
            "entrypoint",
            _normalize_entrypoint(self.entrypoint),
        )
        object.__setattr__(self, "state", _normalize_state(self.state))

        created_at = _require_aware_datetime(self.created_at, field_name="created_at")
        updated_at = _require_aware_datetime(self.updated_at, field_name="updated_at")
        if updated_at < created_at:
            raise ValueError("updated_at must not be before created_at")

        if self.terminal_seq is not None and self.terminal_seq < 1:
            raise ValueError("terminal_seq must be >= 1 when set")

        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)
