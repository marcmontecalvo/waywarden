"""Static grep: no invented approval event types in the repo.

RT-002 defines an exact catalog of 10 event types.  This test prevents
accidental introduction of ``approval_requested`` or ``approval_decided``
event types.
"""

from __future__ import annotations

import pathlib

import pytest

ROOT_PATH = pathlib.Path(__file__).resolve().parent.parent.parent  # repo root
SRC_DIR = ROOT_PATH / "src"

FORBIDDEN_EVENT_TYPES = frozenset(["approval_requested", "approval_decided"])


def test_no_approval_event_types_in_repo() -> None:
    """Scan all .py files under src/waywarden/ for forbidden event types."""
    matched_files: list[str] = []
    for py_file in SRC_DIR.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_EVENT_TYPES:
            if pattern in text:
                matched_files.append(f"{py_file}:{pattern}")

    if matched_files:
        pytest.fail(
            "Found forbidden event types in repo source (RT-002 violation):\n"
            + "\n".join(matched_files)
        )
