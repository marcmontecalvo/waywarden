"""OutputContract — a single declared output contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OutputKind = Literal[
    "file",
    "directory",
    "json",
    "log",
    "patch-set",
    "report",
]


@dataclass(frozen=True, slots=True)
class OutputContract:
    name: str
    path: str
    kind: OutputKind
    required: bool
    promote_to_artifact: bool = True
    description: str | None = None
