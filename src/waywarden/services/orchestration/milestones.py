"""Milestone catalog for orchestration phases.

Every ``run.progress`` ``phase`` / ``milestone`` pair used by the
orchestration service must be declared here.  Callers must use these
constants — free-form strings on ``run.progress`` events are forbidden.

Definition of record:
``docs/orchestration/milestone-catalog.md``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Phase types — these are the five sub-phases of the orchestration run.
ValidPhase = Literal["intake", "plan", "execute", "review", "handoff"]

# Milestone tokens — indexed by phase for type safety.
ValidMilestone = str  # literal values enforced at runtime against MILESTONE_CATALOG


@dataclass(frozen=True, slots=True)
class MilestoneDefinition:
    """Immutable definition of a single milestone within a phase.

    Parameters
    ----------
    phase:
        The orchestration sub-phase this milestone belongs to.
    milestone:
        The stable milestone token (e.g. ``"received"``).
    description:
        Human-readable explanation for documentation surfaces.
    """

    phase: ValidPhase
    milestone: str
    description: str


ALL_PHASES: tuple[ValidPhase, ...] = ("intake", "plan", "execute", "review", "handoff")

MILESTONE_CATALOG: tuple[MilestoneDefinition, ...] = (
    # intake
    MilestoneDefinition("intake", "received", "Task received and parsed by the harness"),
    MilestoneDefinition("intake", "accepted", "Task accepted for processing"),
    # plan
    MilestoneDefinition("plan", "drafted", "Initial plan drafted"),
    MilestoneDefinition("plan", "approval_requested", "Plan submitted for approval gate"),
    MilestoneDefinition("plan", "ready", "Plan approved and ready for execution"),
    # execute
    MilestoneDefinition("execute", "tool_invoked", "A tool invocation starts"),
    MilestoneDefinition("execute", "artifact_emitted", "A tool or step produced an artifact"),
    MilestoneDefinition(
        "execute",
        "waiting_approval",
        "Execution paused at an approval gate",
    ),
    # review
    MilestoneDefinition(
        "review",
        "findings_recorded",
        "Review findings are durably saved",
    ),
    # handoff
    MilestoneDefinition(
        "handoff",
        "envelope_emitted",
        "Delegation envelope registered for child run",
    ),
)

# Fast lookup for validation at runtime.
_MILESTONE_SET: frozenset[tuple[str, str]] = frozenset(
    (md.phase, md.milestone) for md in MILESTONE_CATALOG
)


def is_valid_milestone(phase: str, milestone: str) -> bool:
    """Return ``True`` when *phase*/*milestone* is declared in the catalog."""
    return (phase, milestone) in _MILESTONE_SET


def get_milestones(phase: ValidPhase) -> tuple[str, ...]:
    """Return the milestone tokens for a given phase."""
    return tuple(md.milestone for md in MILESTONE_CATALOG if md.phase == phase)


# Derived constants matching the issue's required milestone names.
MILESTONES: dict[ValidPhase, tuple[str, ...]] = {p: get_milestones(p) for p in ALL_PHASES}
