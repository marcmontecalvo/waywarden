"""Delegation envelope — value type for handing off sub-unit work to a child run.

The envelope is the canonical substrate for RT-001 §Delegated task attachment.
It carries a narrowed manifest intended for the child run, a brief description,
and expected outputs referencing those child manifest outputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from waywarden.domain.ids import DelegationId, RunId
from waywarden.domain.manifest.manifest import WorkspaceManifest

# Fixed createdAt default — overridden by tests via positional argument.
_DEFAULT_CREATED_AT = datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DelegationEnvelope:
    """Opaque delegate for handing a sub-unit of work to a child run.

    This is an immutable value type with zero I/O at construction time.

    Parameters
    ----------
    id:
        Unique delegation identifier.
    parent_run_id:
        The run that created this delegation.
    child_manifest:
        A WorkspaceManifest narrowed from the parent manifest (TSO-011).
    brief:
        Human-readable one-liner describing the sub-unit.
    expected_outputs:
        Names referencing ``child_manifest.outputs`` that the child must produce.
    created_at:
        Creation timestamp.
    """

    id: DelegationId
    parent_run_id: RunId
    child_manifest: WorkspaceManifest
    brief: str
    expected_outputs: Sequence[str]
    created_at: datetime = field(default_factory=lambda: _DEFAULT_CREATED_AT)


def make_envelope(
    parent_run_id: RunId,
    child_manifest: WorkspaceManifest,
    brief: str,
    expected_outputs: Sequence[str],
) -> DelegationEnvelope:
    """Convenience factory for creating a ``DelegationEnvelope``."""
    return DelegationEnvelope(
        id=DelegationId(f"del-{parent_run_id}-1"),
        parent_run_id=parent_run_id,
        child_manifest=child_manifest,
        brief=brief,
        expected_outputs=expected_outputs,
    )
