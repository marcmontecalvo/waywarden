"""SnapshotPolicy — checkpoint and retention policy for the workspace."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SnapshotPolicy:
    on_start: bool = False
    on_completion: bool = True
    on_failure: bool = True
    before_destructive_actions: bool = True
    max_snapshots: int | None = None
    include_paths: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)
