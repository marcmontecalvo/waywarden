"""Approval decision types — tagged union for ApprovalEngine.

Aligned to ADR-0005 and RT-002 approval decision event mapping.
Each branch is a frozen dataclass so the engine treats them as
irreversible decision artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union


@dataclass(frozen=True, slots=True)
class ApprovalAlreadyResolvedError(Exception):
    """Raised when resolve() is called on an already-decided approval."""

    approval_id: str


@dataclass(frozen=True, slots=True)
class Granted:
    """Operator or system has granted the pending approval."""

    decision: Literal["granted"] = "granted"


@dataclass(frozen=True, slots=True)
class DeniedAbandon:
    """Approval denied — operator abandons the action entirely."""

    reason: str
    decision: Literal["denied_abandon"] = "denied_abandon"


@dataclass(frozen=True, slots=True)
class DeniedAlternatePath:
    """Approval denied for this exact action, but an alternate path exists."""

    note: str
    decision: Literal["denied_alternate_path"] = "denied_alternate_path"


@dataclass(frozen=True, slots=True)
class Timeout:
    """Approval expired before a decision was made."""

    retryable: bool
    decision: Literal["timeout"] = "timeout"


ApprovalDecision = Union[  # noqa: UP007
    Granted,
    DeniedAbandon,
    DeniedAlternatePath,
    Timeout,
]
