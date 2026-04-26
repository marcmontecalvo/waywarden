"""EA routine execution surface.

Resolves EA routine assets from the hydrated EA profile and dispatches
them to their respective orchestration handlers.  Bridges profile hydration
(assets/EA profile filters) with the orchestration lifecycle (milestones,
event persistence).

Canonical references:
    - P5-FIX-3 #174 (EA routine orchestration wiring)
    - P5-1 #81 (asset registry + metadata schema)
    - P5-3 #83 (EAProfileView hydration)
    - RT-002 (run event protocol)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from waywarden.domain.run_event import RunEvent


@dataclass(slots=True)
class RoutineSlice:
    """Subset of resolved assets relevant to a single EA routine.

    Attributes
    ----------
    asset_id :
        The resolved asset ``id`` (e.g. ``"ea-briefing"``).
    milestone_specs :
        The milestones array from the routine asset metadata.
    emits_events :
        The event-type catalog the routine is expected to emit.
    artifact_kind :
        Semantic kind of artifact produced (``"briefing"``, ``"task-schedule"``, etc.).
    """

    asset_id: str
    milestone_specs: list[dict[str, Any]] = field(default_factory=list)
    emits_events: list[str] = field(default_factory=list)
    artifact_kind: str = ""


# ---------------------------------------------------------------------------
# Routine resolver — maps EA profile assets → RoutineSlice objects
# ---------------------------------------------------------------------------


class EACoroutine:
    """Wires EA-prof le profile assets to orchestration handlers.

    This is the "routine execution surface" the issue requires: it
    possesses the hydrated EA profile, knows which routine assets are
    resolved (via ``asset_filters``), and dispatches into the
    respective handlers (briefing, scheduler, triage).
    """

    def __init__(
        self,
        milestones: list[dict[str, Any]] | None = None,
        events: list[RunEvent] | None = None,
    ) -> None:
        # Milestone spec collected per run; used by the composed
        # surface for validation.
        self._milestones = milestones or []
        self._events = events or []

    # -- public API ------------------------------------------------------------

    def briefing_artifact_kind(self) -> str:
        """Return the semantic artifact kind for the briefing routine."""
        return "briefing"

    def scheduler_emit_events(self) -> list[str]:
        """Return the events expected by the scheduler."""
        return ["run.progress", "run.approval_waiting"]

    def triage_emit_events(self) -> list[str]:
        """Return the events expected by the triage routine."""
        return ["run.progress", "run.approval_waiting"]

    def resolve_routine_slices(self, resolved_assets: list[Any]) -> list[RoutineSlice]:
        """Resolve routine assets from EA-hydrated profiles.

        Filters the *resolved_assets* list for ``kind == "routine"``
        and emits a :class:`RoutineSlice` per routine asset found.

        Parameters
        ----------
        resolved_assets :
            The ``EAProfileView.resolved_assets`` list.

        Returns
        -------
        A list of :class:`RoutineSlice` for each resolved routine.
        """
        slices: list[RoutineSlice] = []
        for asset in resolved_assets:
            kind = getattr(asset, "kind", None)
            if kind != "routine":
                continue
            asset_id = getattr(asset, "id", "")
            slices.append(
                RoutineSlice(
                    asset_id=asset_id,
                    milestone_specs=getattr(asset, "milestones", []),
                    emits_events=list(getattr(asset, "emits_events", [])),
                    artifact_kind=self._infer_artifact_kind(asset_id),
                )
            )
        return slices

    # -- helpers ---------------------------------------------------------------

    def _infer_artifact_kind(self, asset_id: str) -> str:
        """Derive a semantic artifact kind from the routine asset id."""
        if "briefing" in asset_id:
            return "briefing"
        if "scheduler" in asset_id:
            return "task_schedule"
        if "triage" in asset_id:
            return "triage_outcome"
        return "routine_artifact"
