"""InputMount — a single read-only or explicitly mutable input mount."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InputKind = Literal[
    "file",
    "directory",
    "artifact",
    "bundle",
    "memory-export",
    "knowledge-export",
]


@dataclass(frozen=True, slots=True)
class InputMount:
    name: str
    kind: InputKind
    source_ref: str
    target_path: str
    read_only: bool = True
    required: bool = True
    description: str | None = None
