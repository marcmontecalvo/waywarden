"""Coding-handoff routine.

Builds a coding-specific delegation envelope from the RT-001 manifest
narrowing path and records operator-visible handoff checkpoints as RT-002
``run.progress`` events.
"""

from __future__ import annotations

from datetime import UTC, datetime

from waywarden.domain.delegation.envelope import DelegationEnvelope, make_envelope
from waywarden.domain.delegation.handoff import (
    VALID_CHECKPOINTS,
    HandbackRecord,
    HandoffContext,
)
from waywarden.domain.delegation.narrowing import narrow_manifest
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.repositories import RunEventRepository
from waywarden.domain.run_event import Actor, Causation, RunEvent

ROUTINE_ID = "coding-handoff"
HANDOFF_PHASE = "handoff"
HANDOFF_MILESTONE = "envelope_emitted"
DEFAULT_EXPECTED_OUTPUTS: tuple[str, ...] = ("plan", "patch", "review")


class CodingHandoffRoutine:
    """Routine wrapper for coding-profile delegation handoff.

    The routine is intentionally small: it creates a typed delegation
    envelope, validates child manifest narrowing, and emits the three
    coding handoff checkpoints through the existing RT-002 progress path.
    """

    def __init__(
        self,
        *,
        parent_run_id: str,
        events: RunEventRepository | None = None,
    ) -> None:
        self.parent_run_id = parent_run_id
        self._events = events
        self._envelope: DelegationEnvelope | None = None
        self._records: list[HandbackRecord] = []

    @property
    def envelope(self) -> DelegationEnvelope | None:
        """Return the current delegation envelope, if one has been created."""
        return self._envelope

    def create_envelope(
        self,
        *,
        objective: str,
        parent_manifest: WorkspaceManifest,
        constraints: tuple[str, ...] = (),
        non_goals: tuple[str, ...] = (),
        acceptance_criteria: tuple[str, ...] = (),
        artifact_context: dict[str, object] | None = None,
        expected_outputs: tuple[str, ...] = DEFAULT_EXPECTED_OUTPUTS,
    ) -> DelegationEnvelope:
        """Create a coding handoff envelope with a narrowed child manifest."""
        ctx = HandoffContext(
            objective=objective,
            constraints=constraints,
            non_goals=non_goals,
            acceptance_criteria=acceptance_criteria,
            artifact_context=artifact_context,
        )
        child_manifest = _narrow_child_manifest(parent_manifest)
        narrow_manifest(parent_manifest, child_manifest)
        _validate_expected_outputs(child_manifest, expected_outputs)
        envelope = make_envelope(
            parent_run_id=RunId(self.parent_run_id),
            child_manifest=child_manifest,
            brief=_format_coding_brief(ctx),
            expected_outputs=expected_outputs,
        )
        self._envelope = envelope
        return envelope

    async def record_checkpoint(
        self,
        checkpoint: str,
        summary: str,
    ) -> HandbackRecord:
        """Record and optionally persist a coding handoff checkpoint."""
        if checkpoint not in VALID_CHECKPOINTS:
            raise ValueError(
                f"unknown checkpoint {checkpoint!r}; "
                f"allowed: {', '.join(sorted(VALID_CHECKPOINTS))}"
            )

        timestamp = datetime.now(UTC)
        record = HandbackRecord(
            checkpoint=checkpoint,
            summary=summary,
            timestamp=timestamp,
        )
        self._records.append(record)

        if self._events is not None:
            seq = await self._events.latest_seq(self.parent_run_id) + 1
            await self._events.append(
                RunEvent(
                    id=RunEventId(f"evt-{ROUTINE_ID}-{checkpoint}-{len(self._records)}"),
                    run_id=RunId(self.parent_run_id),
                    seq=seq,
                    type="run.progress",
                    payload={
                        "phase": HANDOFF_PHASE,
                        "milestone": HANDOFF_MILESTONE,
                        "detail": {
                            "checkpoint": checkpoint,
                            "summary": summary,
                            "routine": ROUTINE_ID,
                            "delegation_id": str(self._envelope.id)
                            if self._envelope is not None
                            else None,
                        },
                    },
                    timestamp=timestamp,
                    causation=Causation(
                        event_id=None,
                        action="coding_handoff_checkpoint",
                        request_id=checkpoint,
                    ),
                    actor=Actor(kind="system", id=None, display=None),
                )
            )

        return record

    def get_records(self) -> list[HandbackRecord]:
        """Return a copy of recorded checkpoint history."""
        return list(self._records)


def _narrow_child_manifest(parent: WorkspaceManifest) -> WorkspaceManifest:
    """Build the child manifest used for coding handoff.

    In this phase, the child receives the same concrete grants as the
    already-shaped parent manifest. That is a valid narrowing baseline:
    it introduces no new writable paths, network access, tools, or secrets.
    """
    return WorkspaceManifest(
        run_id=RunId(f"{parent.run_id}-coding-child"),
        inputs=list(parent.inputs),
        writable_paths=list(parent.writable_paths),
        outputs=list(parent.outputs),
        network_policy=parent.network_policy,
        tool_policy=parent.tool_policy,
        secret_scope=parent.secret_scope,
        snapshot_policy=parent.snapshot_policy,
    )


def _validate_expected_outputs(
    child_manifest: WorkspaceManifest,
    expected_outputs: tuple[str, ...],
) -> None:
    output_names = {output.name for output in child_manifest.outputs}
    missing = sorted(set(expected_outputs) - output_names)
    if missing:
        raise ValueError(
            f"expected_outputs must reference child manifest outputs; missing: {', '.join(missing)}"
        )


def _format_coding_brief(ctx: HandoffContext) -> str:
    """Serialize the coding handoff contract into a provider-neutral brief."""
    sections: list[str] = [f"Coding handoff: {ctx.objective}"]
    if ctx.constraints:
        sections.append("Constraints:\n" + "\n".join(f"- {item}" for item in ctx.constraints))
    if ctx.non_goals:
        sections.append("Non-goals:\n" + "\n".join(f"- {item}" for item in ctx.non_goals))
    if ctx.acceptance_criteria:
        sections.append(
            "Acceptance criteria:\n" + "\n".join(f"- {item}" for item in ctx.acceptance_criteria)
        )
    if ctx.artifact_context:
        artifact_lines = [
            f"- {key}: {value}" for key, value in sorted(ctx.artifact_context.items())
        ]
        sections.append("Artifact context:\n" + "\n".join(artifact_lines))
    return "\n\n".join(sections)
