"""Static scan ensuring orchestration code emits only RT-002 catalog event types.

RT-002 §Token usage accounting: Implementations must NOT append
``run.usage`` or similar non-catalog event types.  This test enforces
that constraint with a static grep across ``src/waywarden/``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Event types that must never be emitted.
_FORBIDDEN_PATTERNS: frozenset[str] = frozenset(
    [
        "run\\.usage",
        "run\\.state_changed",
        "run\\.stage_",
        "run\\.task_updated",
    ]
)

_SRC_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "waywarden"


def _grep_for_forbidden_patterns() -> list[str]:
    """Return lines matching any forbidden event type pattern."""
    bad_lines: list[str] = []
    for pattern in _FORBIDDEN_PATTERNS:
        result = subprocess.run(
            [
                "rg",
                "--type=py",
                "--no-heading",
                "--line-number",
                pattern,
                str(_SRC_ROOT),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:  # found matches
            for line in result.stdout.splitlines():
                if "test_no_invented_events" in line:
                    continue
                bad_lines.append(f"{pattern} → {line}")
    return bad_lines


def test_only_catalog_event_types_emitted() -> None:
    """Ensure no forbidden event types appear in source code."""
    bad_lines = _grep_for_forbidden_patterns()
    if bad_lines:
        header = "Orchestration code must only emit RT-002 catalog event types."
        lines = [header]
        lines.extend(f"- {v}" for v in bad_lines)
        raise AssertionError("\n".join(lines))
