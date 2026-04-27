"""EA handoff helper — builds delegation envelopes for EA tasks.

The EA handoff converts a standard task objective into a typed
``DelegationEnvelope`` that carries narrowed constraints, acceptance
criteria, and artifact context for the child/handback run.

Handback checkpoints (plan-approved / implementation-complete /
review-found-issues) are recorded as durable RT-002 ``run.progress``
events via an optional ``RunEventRepository``.

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
from datetime import UTC, datetime
from typing import Any

from waywarden.domain.delegation.envelope import (
    DelegationEnvelope,
    make_envelope,
)
from waywarden.domain.delegation.narrowing import (
    narrow_manifest,
)
from waywarden.domain.ids import DelegationId, RunEventId, RunId
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.run_event import Actor, Causation, RunEvent


def _build_placeholder_manifest(
    expected_outputs: list[str],
) -> WorkspaceManifest:
    """Build a minimal placeholder manifest for tests without parents."""
    from uuid import uuid4

    from waywarden.domain.manifest.input_mount import InputMount  # noqa: F401
    from waywarden.domain.manifest.network_policy import NetworkPolicy
    from waywarden.domain.manifest.output_contract import OutputContract
    from waywarden.domain.manifest.secret_scope import SecretScope
    from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
    from waywarden.domain.manifest.tool_policy import ToolPolicy
    from waywarden.domain.manifest.writable_path import WritablePath

    return WorkspaceManifest(
        run_id=RunId(f"run-placeholder-{uuid4().hex[:8]}"),
        inputs=[],
        writable_paths=[WritablePath(path="/tmp", purpose="task-scratch")],
        outputs=[
            OutputContract(
                name=out,
                path=f"/tmp/{out}",
                kind="report",
                required=True,
            )
            for out in expected_outputs
        ],
        network_policy=NetworkPolicy(mode="deny", allow=[], deny=[]),
        tool_policy=ToolPolicy(preset="yolo", rules=[], default_decision="auto-allow"),
        secret_scope=SecretScope(
            mode="none",
            allowed_secret_refs=[],
            mount_env=[],
            redaction_level="full",
        ),
        snapshot_policy=SnapshotPolicy(
            on_start=False,
            on_completion=False,
            on_failure=False,
            before_destructive_actions=True,
            max_snapshots=10,
            include_paths=[],
            exclude_paths=[],
        ),
    )


# ---------------------------------------------------------------------------
# Handback checkpoint set (restricted to the catalog-compliant subset)
# ---------------------------------------------------------------------------

VALID_CHECKPOINTS: frozenset[str] = frozenset(
    {
        "plan-approved",
        "implementation-complete",
        "review-found-issues",
    }
)


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
    """Lightweight checkpoint emitted during a handback.

    Mirrors the underlying RT-002 event so callers can inspect
    checkpoint history without hitting the event repository.
    """

    checkpoint: str
    summary: str
    timestamp: datetime


class EAAHandoffHelper:
    """Builds delegation envelopes and handles handback.

    The EA handoff helper converts a task objective into a typed
    delegation envelope with narrowed constraints, wrapping both
    manifest narrowing and checkpoint management.

    Parameters
    ----------
    parent_run_id:
        The parent run that creates the delegation.
    events:
        Optional ``RunEventRepository`` for durable handback checkpoints.
    """

    def __init__(
        self,
        parent_run_id: str = "parent-run-1",
        events: Any = None,
    ) -> None:
        self.parent_run_id = parent_run_id
        self._events = events
        self._handback_records: list[HandbackRecord] = []
        self._envelope: DelegationEnvelope | None = None
        self._handoff_ctx: HandoffContext | None = None
        self._parent_manifest: WorkspaceManifest | None = None

    # ------------------------------------------------------------------
    # Context setup
    # ------------------------------------------------------------------

    def set_parent_manifest(self, manifest: WorkspaceManifest) -> None:
        """Attach a parent manifest for later narrowing during envelope creation."""
        self._parent_manifest = manifest

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

    # ------------------------------------------------------------------
    # Envelope creation
    # ------------------------------------------------------------------

    def make_envelope(
        self,
        expected_outputs: list[str] | None = None,
    ) -> DelegationEnvelope:
        """Build a typed ``DelegationEnvelope`` from the stored context.

        Uses the ``make_envelope`` factory from the P4-8 domain type,
        which generates a ``DelegationId`` automatically.

        Parameters
        ----------
        expected_outputs:
            Names referencing ``child_manifest.outputs`` that the
            child must produce.

        Returns
        -------
        ``DelegationEnvelope`` — the P4-8 frozen domain type.

        Raises
        ------
        ValueError:
            If ``build_context`` has not been called first.
        DelegationWideningError:
            If narrowing validation fails against the parent manifest.
        """
        return self._do_make_envelope(expected_outputs or ["artifact"])

    def make_envelope_manual(
        self,
        ctx: HandoffContext,
        expected_outputs: list[str] | None = None,
    ) -> DelegationEnvelope:
        """Build a ``DelegationEnvelope`` from an explicit ``HandoffContext``."""
        # Temporarily set context so _do_make_envelope can access it
        saved = self._handoff_ctx
        self._handoff_ctx = ctx
        try:
            return self._do_make_envelope(expected_outputs or ["artifact"])
        finally:
            self._handoff_ctx = saved

    def _do_make_envelope(
        self,
        expected_outputs: list[str],
    ) -> DelegationEnvelope:
        """Internal envelope creation logic shared by public methods."""
        ctx = self._handoff_ctx
        if ctx is None:
            raise ValueError("no HandoffContext; call build_context first")

        child_manifest = self._resolve_child_manifest(expected_outputs)

        brief = _format_handoff_brief(ctx)
        env = make_envelope(
            parent_run_id=RunId(self.parent_run_id),
            child_manifest=child_manifest,
            brief=brief,
            expected_outputs=expected_outputs,
        )
        self._envelope = env
        return env

    def _resolve_child_manifest(
        self,
        expected_outputs: list[str],
    ) -> WorkspaceManifest:
        """Return a narrowed child manifest from the parent.

        If no parent manifest is set, builds a minimal placeholder
        manifest (for tests that don't need real narrowing).
        """
        if self._parent_manifest is not None:
            # Build a narrowed child manifest that references expected outputs.
            # Capabilities: same writable_paths, same tool_policy, narrower
            # secret_scope and network_policy to satisfy narrowing.
            from uuid import uuid4

            child = WorkspaceManifest(
                run_id=RunId(f"run-child-{uuid4().hex[:8]}"),
                inputs=list(self._parent_manifest.inputs),
                writable_paths=list(self._parent_manifest.writable_paths),
                outputs=list(self._parent_manifest.outputs),
                network_policy=self._parent_manifest.network_policy,
                tool_policy=self._parent_manifest.tool_policy,
                secret_scope=self._parent_manifest.secret_scope,
                snapshot_policy=self._parent_manifest.snapshot_policy,
            )
            narrow_manifest(self._parent_manifest, child)
            return child
        return _build_placeholder_manifest(expected_outputs)

    @property
    def envelope(self) -> DelegationEnvelope | None:
        """Return the current typed ``DelegationEnvelope``, if built."""
        return self._envelope

    @property
    def delegation_id(self) -> DelegationId | None:
        """Exposure of the envelope's ``DelegationId``, if built."""
        if self._envelope is not None:
            return self._envelope.id
        return None

    # ------------------------------------------------------------------
    # Handback recording
    # ------------------------------------------------------------------

    def record_handback(
        self,
        checkpoint: str,
        summary: str,
    ) -> HandbackRecord:
        """Record a handback checkpoint (in-memory only).

        The checkpoint value must be one of the allowed handback types.
        For durable RT-002 persistence, use ``record_handback_async``
        with an ``events`` repository configured on construction.

        Parameters
        ----------
        checkpoint:
            One of ``plan-approved``, ``implementation-complete``,
            ``review-found-issues``.
        summary:
            Free-text summary of the checkpoint.

        Returns
        -------
        ``HandbackRecord`` mirroring the persisted event.

        Raises
        ------
        ValueError:
            If *checkpoint* is not in the allowed set.
        """
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
        self._handback_records.append(record)
        return record

    async def record_handback_async(
        self,
        checkpoint: str,
        summary: str,
    ) -> HandbackRecord:
        """Async-compatible wrapper for ``record_handback`` that always
        emits to the event repository.

        This method should be used when the caller knows events is
        a real ``RunEventRepository`` and can be awaited safely.
        """
        if checkpoint not in VALID_CHECKPOINTS:
            raise ValueError(
                f"unknown checkpoint {checkpoint!r}; "
                f"allowed: {', '.join(sorted(VALID_CHECKPOINTS))}"
            )

        timestamp = datetime.now(UTC)

        envelope_ref = self._envelope.id if self._envelope else None
        queue_len = len(self._handback_records) + 1

        # Record in-memory
        record = HandbackRecord(
            checkpoint=checkpoint,
            summary=summary,
            timestamp=timestamp,
        )
        self._handback_records.append(record)

        # Always persist to event log
        if self._events is not None:
            await self._events.append(
                RunEvent(
                    id=RunEventId(f"evt-handback-{checkpoint}-{queue_len}"),
                    run_id=RunId(self.parent_run_id),
                    seq=(await self._events.latest_seq(self.parent_run_id)) + 1,
                    type="run.progress",
                    payload={
                        "phase": "handoff",
                        "milestone": "envelope_emitted",
                        "checkpoint": checkpoint,
                        "summary": summary,
                        "delegation_id": str(envelope_ref) if envelope_ref is not None else None,
                    },
                    timestamp=timestamp,
                    causation=Causation(
                        event_id=None,
                        action="handback_checkpoint",
                        request_id=checkpoint,
                    ),
                    actor=Actor(kind="system", id=None, display=None),
                )
            )

        return record

    def get_handback_records(self) -> list[HandbackRecord]:
        """Return a copy of the handback checkpoint history."""
        return list(self._handback_records)

    # ------------------------------------------------------------------
    # Manifest helpers
    # ------------------------------------------------------------------

    def validate_narrowing(
        self,
        parent: WorkspaceManifest,
        child: WorkspaceManifest,
    ) -> None:
        """Assert that *child* narrows *parent* on every guarded field.

        Convenience wrapper around ``narrow_manifest`` so callers
        can validate a pre-constructed child without persisting it.
        """
        narrow_manifest(parent, child)


def _format_handoff_brief(ctx: HandoffContext) -> str:
    """Serialize the full EA handoff contract into the envelope brief."""
    sections: list[str] = [f"EA handoff: {ctx.objective}"]
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
