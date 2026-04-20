"""Checkpoint — durable state capture point for runs (RT-002)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from waywarden.domain.ids import CheckpointId, RunId

CheckpointKind = Literal["plan", "pre_approval", "post_execution", "manual", "recovery"]


@dataclass(frozen=True, slots=True)
class Checkpoint:
    id: CheckpointId
    run_id: RunId
    kind: CheckpointKind
    created_at: datetime
    label: str | None = None


def checkpoint_ref(checkpoint: Checkpoint) -> str:
    """Return the RT-002 normative checkpoint reference string."""
    return f"checkpoint://runs/{checkpoint.run_id}/{checkpoint.id}"


def make_checkpoint(
    run_id: RunId,
    kind: CheckpointKind,
    created_at: datetime | None = None,
    label: str | None = None,
) -> Checkpoint:
    """Convenience factory for creating a Checkpoint with a generated ID."""
    return Checkpoint(
        id=CheckpointId(f"ckp_{uuid4().hex[:12]}"),
        run_id=run_id,
        kind=kind,
        created_at=created_at or datetime.now(UTC),
        label=label,
    )
