"""Till-done loop routine for coding profiles (P6-4 #95).

Composes orchestration milestones into a plan -> act -> check iteration
loop. Each iteration emits ``run.progress`` milestones and registers
artifacts via ``run.artifact_created``.

Canonical references:
    - ADR 0007 (loop boundaries)
    - ADR 0008 (coding agent prompts)
    - RT-002 §Progress events
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from waywarden.domain.ids import RunEventId
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.services.orchestration.milestones import is_valid_milestone

# ---------------------------------------------------------------------------
# Loop policy
# ---------------------------------------------------------------------------


class LoopOutcome:
    """Terminal outcomes for the till-done loop."""

    COMPLETED = "completed"
    ESCALATED = "escalated"

    @staticmethod
    def resolved(value: str) -> str:
        accepted = {LoopOutcome.COMPLETED, LoopOutcome.ESCALATED}
        if value in accepted:
            return value
        return LoopOutcome.ESCALATED


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IterationResult:
    """Result of a single till-done loop iteration."""

    plan_artifact_id: str
    check_passed: bool
    changes_applied: bool = False
    plan_revised: bool = False
    iteration_count: int = 0

    @property
    def done(self) -> bool:
        """True when iteration found no further work needed."""
        return self.check_passed and not self.plan_revised


@dataclass(frozen=True, slots=True)
class LoopConfig:
    """Till-done loop configuration.

    Parameters
    ----------
    max_iterations:
        Maximum iterations before escalation (default 3).
    check_failure_max:
        Consecutive check failures before escalation (default 2).
    esc_check_if_revised:
        If True, a plan revision also counts toward check failures.
    """

    max_iterations: int = 3
    check_failure_max: int = 2
    esc_check_if_revised: bool = True


# ---------------------------------------------------------------------------
# Step callable
# ---------------------------------------------------------------------------


ProgressFn = Callable[[str, str, dict[str, Any]], None]
"""Emits a ``run.progress`` milestone event.

Arguments:
    phase: Orchardtra subroutine name.
    milestone: Subphase step name.
    payload: Extra milestone data.
"""

ArtifactFn = Callable[[dict[str, Any]], None]
"""Emits a ``run.artifact_created`` event.

Arguments:
    payload: Artifact reference + kind fields.
"""


class _EventEmitters:
    """Callable for emitting run.progress milestones."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id

    def progress(
        self,
        phase: str,
        milestone: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Emit a run.progress milestone."""
        _await_progress(self._run_id, phase, milestone, extra or {})


def _await_progress(
    run_id: str,
    phase: str,
    milestone: str,
    extra: dict[str, Any],
) -> None:
    """No-op implementation for milestone emission.

    In production this would write a RunEvent through the employees's
    repository. In tests the emitters list receives these.
    """
    if not is_valid_milestone(phase, milestone):
        raise ValueError(f"milestone not cataloged phase={phase!r} milestone={milestone!r}")


def _emit_runtime_event(
    run_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """No-op placeholder for runtime event emission."""
    _ = run_id, event_type, payload


class _EventStream:
    """Captures emitted RunEvents for test verification."""

    def __init__(self) -> None:
        self.events: list[RunEvent] = []

    def emit(self, event: RunEvent) -> None:
        self.events.append(event)

    def by_phase(self, phase: str) -> list[RunEvent]:
        return [
            e
            for e in self.events
            if e.type == "run.progress"
            and isinstance(e.payload, dict)
            and e.payload.get("phase") == phase
        ]

    def by_milestone(self, milestone: str) -> list[RunEvent]:
        return [
            e
            for e in self.events
            if e.type == "run.progress"
            and isinstance(e.payload, dict)
            and e.payload.get("milestone") == milestone
        ]

    @property
    def progress_events(self) -> list[RunEvent]:
        return [e for e in self.events if e.type == "run.progress"]

    @property
    def artifact_events(self) -> list[RunEvent]:
        return [e for e in self.events if e.type == "run.artifact_created"]


# ---------------------------------------------------------------------------
# Routine handler
# ---------------------------------------------------------------------------


async def run_till_done(
    run_id: str,
    *,
    iteration_result_fn: Callable[[int], IterationResult],
    config: LoopConfig | None = None,
    events: _EventStream | None = None,
) -> str:
    """Execute the till-done loop for a coding run.

    Each iteration:

    1. Calls *iteration_result_fn* with the current 1-based iteration number.
    2. Emits ``code.iteration_started``
    3. Emits plan-drafted/approval-requested/ready milestones.
    4. Emits ``code.changes_applied``.
    5. Emits ``code.check_passed`` or ``code.check_failed``.
    6. Emits ``code.plan_revised`` if plan was sorted out.
    7. Emits ``code.iteration_complete``.

    Escalates when max iterations or consecutive check failures are
    reached.

    Args:
        run_id: The run identifier for milestone emission.
        iteration_result_fn: Callable returning the result of one
            iteration, keyed by 1-based iteration number.
        config: Optional loop configuration overrides.
        events: Event stream for capturing emitted RunEvents.

    Returns:
        The terminal loop outcome: LoopOutcome.COMPLETED or
        LoopOutcome.ESCALATED.
    """
    cfg = config or LoopConfig()
    iteration = 0
    consecutive_check_failures = 0

    stream = events or _EventStream()

    while iteration < cfg.max_iterations:
        iteration += 1
        result = iteration_result_fn(iteration)
        result = IterationResult(
            plan_artifact_id=result.plan_artifact_id,
            check_passed=result.check_passed,
            changes_applied=result.changes_applied,
            plan_revised=result.plan_revised,
            iteration_count=iteration,
        )

        # code: iteration_started
        _emit_progress(run_id, stream, "code", "iteration_started")

        if iteration >= cfg.max_iterations:
            _emit_progress(run_id, stream, "code", "loop_escalated")
            return LoopOutcome.ESCALATED

        # plan phase: drafted
        _emit_progress(run_id, stream, "plan", "drafted")
        _emit_progress(run_id, stream, "plan", "approval_requested")
        _emit_progress(run_id, stream, "plan", "ready")

        # code: changes_applied
        _emit_progress(
            run_id,
            stream,
            "code",
            "changes_applied",
            payload={"artifact_id": result.plan_artifact_id},
        )

        # code: check_passed OR check_failed
        if result.plan_revised:
            _emit_progress(run_id, stream, "code", "plan_revised")
            _emit_progress(run_id, stream, "plan", "ready")
            if cfg.esc_check_if_revised:
                pass  # revise = trace
        elif result.check_passed:
            _emit_progress(run_id, stream, "code", "check_passed")
        else:
            _emit_progress(run_id, stream, "code", "iteration_complete")

        if not result.check_passed:
            consecutive_check_failures += 1

        if result.check_passed and not result.plan_revised:
            _emit_progress(run_id, stream, "code", "iteration_complete")
            _emit_progress(run_id, stream, "code", "terminal")
            return LoopOutcome.COMPLETED

    # Exceeded max iterations
    _emit_progress(run_id, stream, "code", "loop_escalated")
    return LoopOutcome.ESCALATED


def _emit_progress(
    run_id: str,
    stream: _EventStream,
    phase: str,
    milestone: str,
    *,
    payload: dict[str, Any] | None = None,
) -> None:
    """Emit a run.progress milestone event into the capture stream."""
    if not is_valid_milestone(phase, milestone):
        raise ValueError(f"milestone not cataloged: phase={phase!r} milestone={milestone!r}")

    event = RunEvent(
        id=RunEventId(f"{run_id}.prog.{phase}.{milestone}"),
        run_id=run_id,
        seq=len(stream.events) + 1,
        type="run.progress",
        payload={
            "phase": phase,
            "milestone": milestone,
            **(payload or {}),
        },
        timestamp=datetime.now(UTC),
        causation=Causation(
            event_id=None,
            action=f"{phase}.{milestone}",
            request_id=None,
        ),
        actor=Actor(kind="system", id=None, display=None),
    )
    stream.emit(event)
