"""WritablePath — a single writable path grant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

WritablePurpose = Literal["task-scratch", "declared-output", "cache", "checkout-copy"]
Retention = Literal["ephemeral", "run-retained", "artifact-promoted"]


@dataclass(frozen=True, slots=True)
class WritablePath:
    path: str
    purpose: WritablePurpose
    max_size_mb: int | None = None
    retention: Retention | None = None
