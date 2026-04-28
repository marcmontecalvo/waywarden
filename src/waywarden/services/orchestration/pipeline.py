"""Pipeline execution over existing RT-002 orchestration milestones."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from waywarden.domain.durability import TokenBudgetTelemetry, token_budget_payload
from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.pipeline import (
    Pipeline,
    PipelineExecutionStatus,
    PipelineNode,
    PipelineNodeId,
    PipelineOutcome,
)
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.services.orchestration.milestones import is_valid_milestone


@dataclass(frozen=True, slots=True)
class PipelineExecutionResult:
    """Result of deterministic pipeline execution planning."""

    status: PipelineExecutionStatus
    visited_node_ids: tuple[str, ...]
    events: tuple[RunEvent, ...]


class PipelineExecutionEngine:
    """Executes a provider-neutral pipeline by composing catalog milestones.

    The engine does not call model providers or channel adapters. Callers supply
    node outcomes, and the engine records the deterministic route through the
    pipeline as RT-002 ``run.progress`` events.
    """

    def __init__(self, *, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or (lambda: datetime.now(UTC))

    def execute(
        self,
        *,
        pipeline: Pipeline,
        run_id: RunId,
        outcomes: Mapping[str, PipelineOutcome],
        correlation: RunCorrelation | None = None,
        token_budget: TokenBudgetTelemetry | None = None,
        max_steps: int | None = None,
    ) -> PipelineExecutionResult:
        """Execute *pipeline* using supplied per-node outcomes."""
        visited: list[str] = []
        events: list[RunEvent] = []
        current_id: PipelineNodeId | None = cast(PipelineNodeId, pipeline.start_node)
        status: PipelineExecutionStatus = "completed"
        step_limit = max_steps if max_steps is not None else max(len(pipeline.nodes) * 2, 1)
        if step_limit < 1:
            raise ValueError("max_steps must be greater than zero")

        while current_id is not None:
            if len(visited) >= step_limit:
                raise ValueError("pipeline execution exceeded max_steps")
            node = pipeline.node(current_id)
            outcome = self._outcome_for(node, outcomes)
            route = pipeline.route(node.id, outcome)
            next_id = route.to_node
            node_status: PipelineExecutionStatus | str = "completed"
            if outcome == "failure" and next_id is None:
                node_status = "aborted"
                status = "aborted"

            visited.append(str(node.id))
            events.append(
                self._make_progress_event(
                    run_id=run_id,
                    pipeline=pipeline,
                    node=node,
                    seq=len(events) + 1,
                    outcome=outcome,
                    status=node_status,
                    correlation=correlation,
                    token_budget=token_budget,
                )
            )
            if status == "aborted":
                break
            current_id = cast(PipelineNodeId | None, next_id)

        return PipelineExecutionResult(
            status=status,
            visited_node_ids=tuple(visited),
            events=tuple(events),
        )

    @staticmethod
    def _outcome_for(
        node: PipelineNode,
        outcomes: Mapping[str, PipelineOutcome],
    ) -> PipelineOutcome:
        try:
            return outcomes[str(node.id)]
        except KeyError as exc:
            raise KeyError(f"missing outcome for pipeline node {node.id!r}") from exc

    def _make_progress_event(
        self,
        *,
        run_id: RunId,
        pipeline: Pipeline,
        node: PipelineNode,
        seq: int,
        outcome: PipelineOutcome,
        status: str,
        correlation: RunCorrelation | None,
        token_budget: TokenBudgetTelemetry | None,
    ) -> RunEvent:
        if not is_valid_milestone(node.phase, node.milestone):
            raise ValueError(
                f"milestone not cataloged: phase={node.phase!r} milestone={node.milestone!r}"
            )
        payload: dict[str, object] = {
            "phase": node.phase,
            "milestone": node.milestone,
            "milestone_ref": f"{node.phase}.{node.milestone}",
            "run_id": str(run_id),
            "pipeline_id": str(pipeline.id),
            "node_id": str(node.id),
            "node_kind": node.kind,
            "ref_id": node.ref_id,
            "input_artifact_kind": node.input_artifact_kind,
            "output_artifact_kind": node.output_artifact_kind,
            "outcome": outcome,
            "status": status,
        }
        if correlation is not None:
            payload.update(correlation.as_payload())
        budget_payload = token_budget_payload(token_budget)
        if budget_payload is not None:
            payload["token_budget"] = budget_payload

        return RunEvent(
            id=RunEventId(f"evt-{run_id}-{pipeline.id}-{node.id}-{uuid4().hex}"),
            run_id=run_id,
            seq=seq,
            type="run.progress",
            payload=payload,
            timestamp=self._now(),
            causation=Causation(
                event_id=None,
                action=f"pipeline.{node.kind}.{outcome}",
                request_id=str(pipeline.id),
            ),
            actor=Actor(kind="system", id=str(pipeline.id), display=str(pipeline.id)),
        )


__all__ = ["PipelineExecutionEngine", "PipelineExecutionResult"]
