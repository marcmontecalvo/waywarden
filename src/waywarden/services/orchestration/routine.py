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
from typing import TYPE_CHECKING, Any

from waywarden.domain.run_event import RunEvent

if TYPE_CHECKING:
    from waywarden.domain.repositories import RunEventRepository
    from waywarden.services.ea_task_service import EATaskService


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
        *,
        task_service: EATaskService | None = None,
        event_repo: RunEventRepository | None = None,
    ) -> None:
        # Milestone spec collected per run; used by the composed
        # surface for validation.
        self._milestones = milestones or []
        self._events = events or []
        self._task_service = task_service
        self._event_repo = event_repo

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

    async def execute(
        self,
        asset_id: str,
        resolved_assets: list[Any],
        **kwargs: Any,
    ) -> Any:
        """Execute a resolved EA routine asset through its handler.

        The asset must be present in the hydrated profile's
        ``resolved_assets`` and must have ``kind == "routine"``. This keeps
        direct handler calls out of the profile-owned orchestration path.
        """
        routine = self._require_routine(asset_id, resolved_assets)
        normalized_id = routine.asset_id.replace("_", "-")
        if "briefing" in normalized_id:
            from waywarden.services.orchestration.briefing import EABriefingHandler

            briefing_handler = EABriefingHandler(event_repo=self._event_repo, events=self._events)
            return await briefing_handler.run_async(
                inbox_entries=kwargs.get("inbox_entries"),
                pending_tasks=kwargs.get("pending_tasks", 0),
                run_id=kwargs.get("run_id", "ea-briefing-run"),
            )
        if "scheduler" in normalized_id:
            from waywarden.services.orchestration.scheduler import EASchedulerHandler

            if self._task_service is None:
                raise ValueError("scheduler routine requires task_service")
            scheduler_handler = EASchedulerHandler(task_service=self._task_service)
            return await scheduler_handler.run(
                tasks=kwargs.get("tasks", []),
                decisions=kwargs.get("decisions"),
                run_id=kwargs.get("run_id", "ea-scheduler-run"),
            )
        if "triage" in normalized_id:
            from waywarden.services.orchestration.triage import EAIboxTriageHandler

            if self._task_service is None:
                raise ValueError("triage routine requires task_service")
            triage_handler = EAIboxTriageHandler(task_service=self._task_service)
            return await triage_handler.run(
                items=kwargs.get("items", []),
                decisions=kwargs.get("decisions"),
                run_id=kwargs.get("run_id", "ea-triage-run"),
            )
        raise ValueError(f"no EA routine handler registered for asset {asset_id!r}")

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

    def _require_routine(self, asset_id: str, resolved_assets: list[Any]) -> RoutineSlice:
        for routine in self.resolve_routine_slices(resolved_assets):
            if routine.asset_id == asset_id:
                return routine
        raise ValueError(f"routine asset {asset_id!r} was not resolved by EA profile")
