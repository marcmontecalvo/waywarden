"""Approval engine — interprets ADR-0005 presets, emits RT-002 events.

The ApprovalEngine is the only component authorized to transition runs
through the ``waiting_approval`` state and to emit the precise
approval decision events from RT-002.

Canonical references
--------------------
- ADR-0005: approval model
- RT-002 §Approval decision event mapping
- ``src/waywarden/domain/approval.py``: ``Approval`` domain model
- ``src/waywarden/domain/run_event.py``: ``RunEvent`` envelope
- ``src/waywarden/domain/run_event_types.py``: exact event type catalog
- ``src/waywarden/domain/repositories/protocols.py``: repo protocols
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging import getLogger
from typing import TYPE_CHECKING, cast

from waywarden.domain.approval import Approval
from waywarden.domain.ids import ApprovalId, RunEventId, RunId
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.run_event_types import RunEventType
from waywarden.services.approval_types import (
    ApprovalAlreadyResolvedError,
    ApprovalDecision,
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
    Timeout,
)

if TYPE_CHECKING:
    from waywarden.domain.repositories import ApprovalRepository, RunEventRepository

logger = getLogger(__name__)

# Approved decision_reviver mapping — maps each ApprovalDecision variant
# to the RT-002 event(s) it produces.
# This is the canonical mapping; any future change must update RT-002 first.


def _next_event_type(type_hint: str) -> RunEventType:
    """Return a type-hinted RunEventType from a string.

    The return value is one of the 10 approved RT-002 event types.
    """
    return cast(RunEventType, type_hint)


@dataclass(frozen=True, slots=True)
class ApprovalEngine:
    """Stateless engine that persists approvals and emits RT-002 events.

    Parameters
    ----------
    approvals:
        Repository for ``Approval`` persisted artifacts.
    events:
        Append-only event log (RT-002).
    """

    approvals: ApprovalRepository = field(repr=False)
    events: RunEventRepository = field(repr=False)

    async def request(
        self,
        run_id: str,
        approval_kind: str,
        summary: str,
        *,
        requested_capability: str | None = None,
        expires_at: datetime | None = None,
        checkpoint_ref: str | None = None,
    ) -> Approval:
        """Persist a new approval in ``pending`` state and emit
        ``run.approval_waiting``.

        Parameters
        ----------
        run_id:
            The run that requires approval.
        approval_kind:
            Human-readable category for the approval request.
        summary:
            Brief description of what is being approved.
        requested_capability:
            Optional capability string from ADR-0005.
        expires_at:
            Optional timezone-aware expiry.
        checkpoint_ref:
            Optional checkpoint reference.

        Returns
        -------
        The persisted ``Approval`` in ``pending`` state.
        """
        now = datetime.now(UTC)
        approval_id_str = f"approval-{run_id}-{approval_kind}"

        approval = Approval(
            id=ApprovalId(approval_id_str),
            run_id=RunId(run_id),
            approval_kind=approval_kind,
            requested_capability=requested_capability,
            summary=summary,
            state="pending",
            requested_at=now,
            decided_at=None,
            decided_by=None,
            expires_at=expires_at,
        )

        # Persist the approval record
        saved = await self.approvals.save(approval)

        # Append the approval_waiting event to the run event log
        payload: dict[str, object] = {
            "approval_id": saved.id,
            "approval_kind": saved.approval_kind,
            "summary": saved.summary,
        }

        if saved.requested_capability is not None:
            payload["requested_capability"] = saved.requested_capability

        if checkpoint_ref is not None:
            payload["checkpoint_ref"] = checkpoint_ref

        event = RunEvent(
            id=RunEventId(f"evt-{saved.id}-waiting"),
            run_id=RunId(run_id),
            seq=(await self.events.latest_seq(run_id)) + 1,
            type=_next_event_type("run.approval_waiting"),
            payload=payload,
            timestamp=now,
            causation=Causation(event_id=None, action="request_approval", request_id=None),
            actor=Actor(kind="system", id=None, display=None),
        )

        await self.events.append(event)
        return saved

    async def resolve(
        self,
        approval_id: str,
        decision: ApprovalDecision,
    ) -> RunEvent:
        """Resolve a pending approval and emit the mapped RT-002 event.

        Parameters
        ----------
        approval_id:
            The approval to resolve.
        decision:
            One of ``Granted``, ``DeniedAbandon``,
            ``DeniedAlternatePath``, or ``Timeout``.

        Returns
        -------
        The emitted ``RunEvent`` for the decision.

        Raises
        ------
        ApprovalAlreadyResolvedError:
            If the approval is already in ``granted``, ``denied``, or
            ``timeout`` state.
        """
        # Load existing approval
        existing = await self.approvals.get(approval_id)
        if existing is None:
            # Safety: rejection for an approval not associated with any run
            raise RuntimeError(f"Approval {approval_id!r} not found")

        # Reject double-resolve
        if existing.state != "pending":
            raise ApprovalAlreadyResolvedError(approval_id=existing.id)

        now = datetime.now(UTC)
        decision_tag = decision.decision
        new_state_map: dict[str, str] = {
            "granted": "granted",
            "denied_abandon": "denied",
            "denied_alternate_path": "denied",
            "timeout": "timeout",
        }
        new_state = new_state_map.get(decision_tag)
        if new_state is None:
            raise RuntimeError(f"Unexpected decision type: {decision_tag!r}")

        # Update approval state
        updated = Approval(
            id=existing.id,
            run_id=existing.run_id,
            approval_kind=existing.approval_kind,
            requested_capability=existing.requested_capability,
            summary=existing.summary,
            state=new_state,  # type: ignore[arg-type]
            requested_at=existing.requested_at,
            decided_at=now,
            decided_by=existing.decided_by,
            expires_at=existing.expires_at,
        )

        await self.approvals.save(updated)

        # Emit the mapped event based on the decision variant
        if decision.decision == "granted":
            return await self._emit_granted(existing, decision, now)
        elif decision.decision == "denied_abandon":
            return await self._emit_denied_abandon(existing, decision, now)
        elif decision.decision == "denied_alternate_path":
            return await self._emit_denied_alternate(existing, decision, now)
        elif decision.decision == "timeout":
            return await self._emit_timeout(existing, decision, now)
        else:
            raise RuntimeError(f"Unexpected decision type: {decision.decision}")

    # -- private event emission methods -------------------------------------

    async def _emit_granted(
        self,
        approval: Approval,
        decision: Granted,
        now: datetime,
    ) -> RunEvent:
        """``run.resumed(resume_kind=approval_granted)``."""
        last_seq = await self.events.latest_seq(approval.run_id)
        next_seq = last_seq + 1
        event = RunEvent(
            id=RunEventId(f"evt-{approval.id}-granted"),
            run_id=approval.run_id,
            seq=next_seq,
            type=_next_event_type("run.resumed"),
            payload={
                "resume_kind": "approval_granted",
                "resumed_from_seq": last_seq,
                "approval_id": approval.id,
            },
            timestamp=now,
            causation=Causation(event_id=None, action="approve_decision", request_id=None),
            actor=Actor(kind="operator", id=None, display=None),
        )
        return await self.events.append(event)

    async def _emit_denied_abandon(
        self,
        approval: Approval,
        decision: DeniedAbandon,
        now: datetime,
    ) -> RunEvent:
        """``run.cancelled(reason="approval_denied")``."""
        next_seq = (await self.events.latest_seq(approval.run_id)) + 1
        event = RunEvent(
            id=RunEventId(f"evt-{approval.id}-denied_abandon"),
            run_id=approval.run_id,
            seq=next_seq,
            type=_next_event_type("run.cancelled"),
            payload={
                "reason": "approval_denied",
            },
            timestamp=now,
            causation=Causation(event_id=None, action="deny_decision", request_id=None),
            actor=Actor(kind="operator", id=None, display=None),
        )
        return await self.events.append(event)

    async def _emit_denied_alternate(
        self,
        approval: Approval,
        decision: DeniedAlternatePath,
        now: datetime,
    ) -> RunEvent:
        """``run.resumed(resume_kind=approval_denied_alternate_path)``."""
        last_seq = await self.events.latest_seq(approval.run_id)
        next_seq = last_seq + 1
        event = RunEvent(
            id=RunEventId(f"evt-{approval.id}-denied_alternate"),
            run_id=approval.run_id,
            seq=next_seq,
            type=_next_event_type("run.resumed"),
            payload={
                "resume_kind": "approval_denied_alternate_path",
                "resumed_from_seq": last_seq,
                "approval_id": approval.id,
            },
            timestamp=now,
            causation=Causation(event_id=None, action="deny_alternate", request_id=None),
            actor=Actor(kind="operator", id=None, display=None),
        )
        return await self.events.append(event)

    async def _emit_timeout(
        self,
        approval: Approval,
        decision: Timeout,
        now: datetime,
    ) -> RunEvent:
        """Map ``Timeout(retryable)`` to either ``run.failed`` or
        ``run.cancelled``.

        - ``retryable=True`` → ``run.failed(failure_code="approval_timeout", retryable=True)``
        - ``retryable=False`` → ``run.cancelled(reason="approval_timeout")``
        """
        if decision.retryable:
            next_seq = (await self.events.latest_seq(approval.run_id)) + 1
            event = RunEvent(
                id=RunEventId(f"evt-{approval.id}-timeout_retry"),
                run_id=approval.run_id,
                seq=next_seq,
                type=_next_event_type("run.failed"),
                payload={
                    "failure_code": "approval_timeout",
                    "message": "approval timed out",
                    "retryable": True,
                },
                timestamp=now,
                causation=Causation(event_id=None, action="timeout_retry", request_id=None),
                actor=Actor(kind="system", id=None, display=None),
            )
        else:
            next_seq = (await self.events.latest_seq(approval.run_id)) + 1
            event = RunEvent(
                id=RunEventId(f"evt-{approval.id}-timeout"),
                run_id=approval.run_id,
                seq=next_seq,
                type=_next_event_type("run.cancelled"),
                payload={
                    "reason": "approval_timeout",
                },
                timestamp=now,
                causation=Causation(event_id=None, action="timeout_noretry", request_id=None),
                actor=Actor(kind="system", id=None, display=None),
            )
        return await self.events.append(event)
