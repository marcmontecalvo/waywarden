"""Assert Run does not expose a stage or phase domain axis.

RT-002 defines seven canonical run states — no additional axis like
``stage`` or ``phase`` exists on the ``Run`` dataclass.
"""

from __future__ import annotations

from dataclasses import fields

from waywarden.domain.run import Run


def test_run_state_axis_is_rt002() -> None:
    """Run must not have a ``stage`` or ``phase`` field."""
    field_names = {f.name for f in fields(Run)}
    assert "stage" not in field_names, "Run must not expose a 'stage' field"
    assert "phase" not in field_names, "Run must not expose a 'phase' field"
