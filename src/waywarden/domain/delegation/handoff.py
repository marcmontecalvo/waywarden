"""EA handoff helper — builds delegation envelopes for EA tasks.

The EA handoff converts a standard task objective into a typed
``DelegationEnvelope`` that carries narrowed constraints, acceptance
criteria, and artifact context for the child/handback run.

Handback checkpoints (plan-approved / implementation-complete /
review-found-issues) are recorded via ``run.progress`` milestones.

The handoff helper is designed so that its core logic (envelope fields,
handback recording, manifest narrowing) can be unit-tested without
needing full runtime manifests.

Canonical references:
    - RT-001 §Delegated task attachment
    - RT-002 (event types)
    - P4-8 / #71 (DelegationEnvelope)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HandoffContext:
    """Inputs needed to build a delegation envelope.

    This is the EA-facing contract: objective, constraints, non-goals,
    and acceptance criteria.
    """

    objective: str
    constraints: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    artifact_context: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class HandbackRecord:
    """Lightweight checkpoint emitted during a handback."""

    checkpoint: str  # plan-approved / implementation-complete / review-found-issues
    summary: str
    timestamp: str  # ISO format


class EAAHandoffHelper:
    """Builds delegation envelopes and handles handback.

    The EA handoff helper converts a task objective into a typed
    delegation envelope with narrowed constraints, wrapping both
    manifest narrowing and checkpoint management.

    The ``delegation_id`` and ``envelope`` properties are populated
    lazily after the first ``make_envelope`` call.
    """

    def __init__(
        self,
        parent_run_id: str = "parent-run-1",
    ) -> None:
        self.parent_run_id = parent_run_id
        self._handback_records: list[HandbackRecord] = []
        self._envelope: dict[str, Any] | None = None
        self._handoff_ctx: HandoffContext | None = None

    def build_context(
        self,
        objective: str,
        constraints: tuple[str, ...] | None = None,
        non_goals: tuple[str, ...] | None = None,
        acceptance_criteria: tuple[str, ...] | None = None,
        artifact_context: dict[str, Any] | None = None,
    ) -> HandoffContext:
        """Create and store a handoff context for later envelope building."""
        ctx = HandoffContext(
            objective=objective,
            constraints=constraints or (),
            non_goals=non_goals or (),
            acceptance_criteria=acceptance_criteria or (),
            artifact_context=artifact_context,
        )
        self._handoff_ctx = ctx
        return ctx

    def make_envelope(
        self,
        expected_outputs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build a simplified delegation envelope dict.

        Returns a dict representation (not the full DelegationEnvelope
        type, which requires runtime manifests) for testability.
        """
        ctx = self._handoff_ctx
        if ctx is None:
            raise ValueError("no HandoffContext; call build_context first")

        outputs = expected_outputs or ["artifact"]
        brief = f"EA handoff: {ctx.objective}"
        from datetime import UTC
        from datetime import datetime as _dt

        now = _dt.now(UTC).isoformat()

        self._envelope = {
            "parent_run_id": self.parent_run_id,
            "brief": brief,
            "expected_outputs": outputs,
            "constraints": ctx.constraints,
            "non_goals": ctx.non_goals,
            "acceptance_criteria": ctx.acceptance_criteria,
            "artifact_context": ctx.artifact_context or {},
            "created_at": now,
        }
        return self._envelope

    def make_envelope_manual(
        self,
        ctx: HandoffContext,
        expected_outputs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build an envelope from an explicit HandoffContext."""
        outputs = expected_outputs or ["artifact"]
        brief = f"EA handoff: {ctx.objective}"
        from datetime import UTC
        from datetime import datetime as _dt

        now = _dt.now(UTC).isoformat()

        self._envelope = {
            "parent_run_id": self.parent_run_id,
            "brief": brief,
            "expected_outputs": outputs,
            "constraints": ctx.constraints,
            "non_goals": ctx.non_goals,
            "acceptance_criteria": ctx.acceptance_criteria,
            "artifact_context": ctx.artifact_context or {},
            "created_at": now,
        }
        return self._envelope

    @property
    def envelope(self) -> dict[str, Any] | None:
        return self._envelope

    def record_handback(
        self,
        checkpoint: str,
        summary: str,
    ) -> HandbackRecord:
        """Record a handback checkpoint."""
        import datetime

        record = HandbackRecord(
            checkpoint=checkpoint,
            summary=summary,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        self._handback_records.append(record)
        return record

    def get_handback_records(self) -> list[HandbackRecord]:
        return list(self._handback_records)
