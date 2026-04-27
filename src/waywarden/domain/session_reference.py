"""Domain model for coding-session continuity references.

A session reference ties a conversation message to an artifact and run for
resume across sessions. No new runtime domain state axis is introduced —
this is purely reference metadata.

Canonical references:
    - RT-001, RT-002
    - P6-1 #92
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class SessionReference:
    """Immutable reference tying a message to an artifact and run.

    Keyed by (run_id, artifact_id).
    """

    run_id: str
    artifact_id: str
    session_ref: str  # external message / conversation reference
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if not self.artifact_id:
            raise ValueError("artifact_id must not be empty")
        if not self.session_ref:
            raise ValueError("session_ref must not be empty")

    @property
    def composite_key(self) -> str:
        """Return a composite key for this reference."""
        return f"{self.run_id}:{self.artifact_id}"
