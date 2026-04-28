"""Provider-neutral pipeline domain primitive.

Pipelines compose sub-agents and teams through typed artifact boundaries and
review checkpoints. They intentionally reuse RT-002 orchestration milestones
instead of introducing a provider-specific runtime or a new run state axis.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, NewType, Self, cast

from waywarden.domain.handoff import HandoffArtifact
from waywarden.services.orchestration.milestones import ValidPhase, is_valid_milestone

PipelineId = NewType("PipelineId", str)
PipelineNodeId = NewType("PipelineNodeId", str)
PipelineNodeKind = Literal["sub_agent", "team", "review_checkpoint"]
PipelineOutcome = Literal["success", "failure"]
PipelineExecutionStatus = Literal["completed", "aborted"]


def _clean_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


@dataclass(frozen=True, slots=True)
class ReviewCheckpoint:
    """Typed review checkpoint input and output boundary."""

    input_artifact_kind: str
    passed_output_artifact_kind: str
    failed_output_artifact_kind: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_artifact_kind",
            _clean_text(self.input_artifact_kind, field_name="input_artifact_kind"),
        )
        object.__setattr__(
            self,
            "passed_output_artifact_kind",
            _clean_text(
                self.passed_output_artifact_kind,
                field_name="passed_output_artifact_kind",
            ),
        )
        object.__setattr__(
            self,
            "failed_output_artifact_kind",
            _clean_text(
                self.failed_output_artifact_kind,
                field_name="failed_output_artifact_kind",
            ),
        )


@dataclass(frozen=True, slots=True)
class PipelineNode:
    """One executable pipeline node over an existing orchestration milestone."""

    id: PipelineNodeId | str
    kind: PipelineNodeKind
    ref_id: str
    input_artifact_kind: str
    output_artifact_kind: str
    phase: ValidPhase
    milestone: str
    review_checkpoint: ReviewCheckpoint | None = None

    def __post_init__(self) -> None:
        node_id = PipelineNodeId(_clean_text(self.id, field_name="id"))
        kind = _clean_text(self.kind, field_name="kind")
        if kind not in {"sub_agent", "team", "review_checkpoint"}:
            raise ValueError("kind must be one of sub_agent, team, review_checkpoint")
        phase = _clean_text(self.phase, field_name="phase")
        milestone = _clean_text(self.milestone, field_name="milestone")
        if not is_valid_milestone(phase, milestone):
            raise ValueError(f"milestone not cataloged: phase={phase!r} milestone={milestone!r}")

        checkpoint = self.review_checkpoint
        if kind == "review_checkpoint":
            if checkpoint is None:
                raise ValueError("review_checkpoint nodes require review_checkpoint")
            if checkpoint.input_artifact_kind != self.input_artifact_kind:
                raise ValueError("review checkpoint input must match node input_artifact_kind")
        elif checkpoint is not None:
            raise ValueError("review_checkpoint is only valid for review_checkpoint nodes")

        object.__setattr__(self, "id", node_id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "ref_id", _clean_text(self.ref_id, field_name="ref_id"))
        object.__setattr__(
            self,
            "input_artifact_kind",
            _clean_text(self.input_artifact_kind, field_name="input_artifact_kind"),
        )
        object.__setattr__(
            self,
            "output_artifact_kind",
            _clean_text(self.output_artifact_kind, field_name="output_artifact_kind"),
        )
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "milestone", milestone)


@dataclass(frozen=True, slots=True)
class PipelineRoute:
    """Outcome route from one node to another or to a terminal state."""

    from_node: PipelineNodeId | str
    outcome: PipelineOutcome
    to_node: PipelineNodeId | str | None

    def __post_init__(self) -> None:
        outcome = _clean_text(self.outcome, field_name="outcome")
        if outcome not in {"success", "failure"}:
            raise ValueError("outcome must be one of success, failure")
        object.__setattr__(
            self,
            "from_node",
            PipelineNodeId(_clean_text(self.from_node, field_name="from_node")),
        )
        object.__setattr__(self, "outcome", outcome)
        if self.to_node is not None:
            object.__setattr__(
                self,
                "to_node",
                PipelineNodeId(_clean_text(self.to_node, field_name="to_node")),
            )


@dataclass(frozen=True, slots=True)
class Pipeline:
    """Composable pipeline of teams, sub-agents, and review checkpoints."""

    id: PipelineId | str
    start_node: PipelineNodeId | str
    nodes: tuple[PipelineNode, ...]
    routes: tuple[PipelineRoute, ...] = ()

    def __post_init__(self) -> None:
        pipeline_id = PipelineId(_clean_text(self.id, field_name="id"))
        start_node = PipelineNodeId(_clean_text(self.start_node, field_name="start_node"))
        nodes = tuple(self.nodes)
        if not nodes:
            raise ValueError("nodes must not be empty")
        if any(not isinstance(node, PipelineNode) for node in nodes):
            raise TypeError("nodes must contain PipelineNode values")

        node_by_id: dict[PipelineNodeId, PipelineNode] = {}
        for node in nodes:
            node_id = cast(PipelineNodeId, node.id)
            if node_id in node_by_id:
                raise ValueError(f"duplicate pipeline node {node_id!r}")
            node_by_id[node_id] = node
        if start_node not in node_by_id:
            raise ValueError("start_node references unknown node")

        routes = tuple(self.routes)
        route_keys: set[tuple[PipelineNodeId, PipelineOutcome]] = set()
        for route in routes:
            if not isinstance(route, PipelineRoute):
                raise TypeError("routes must contain PipelineRoute values")
            from_node = cast(PipelineNodeId, route.from_node)
            to_node = cast(PipelineNodeId | None, route.to_node)
            if from_node not in node_by_id:
                raise ValueError("route references unknown from_node")
            if to_node is not None and to_node not in node_by_id:
                raise ValueError("route references unknown to_node")
            key = (from_node, route.outcome)
            if key in route_keys:
                raise ValueError("duplicate route for node outcome")
            route_keys.add(key)

        object.__setattr__(self, "id", pipeline_id)
        object.__setattr__(self, "start_node", start_node)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "routes", routes)

    def node(self, node_id: PipelineNodeId | str) -> PipelineNode:
        """Return a node by id."""
        key = PipelineNodeId(_clean_text(node_id, field_name="node_id"))
        for node in self.nodes:
            if node.id == key:
                return node
        raise KeyError(f"unknown pipeline node {key!r}")

    def route(self, from_node: PipelineNodeId | str, outcome: PipelineOutcome) -> PipelineRoute:
        """Return the route for a node outcome."""
        clean_from_node = PipelineNodeId(_clean_text(from_node, field_name="from_node"))
        clean_outcome = _clean_text(outcome, field_name="outcome")
        for route in self.routes:
            if route.from_node == clean_from_node and route.outcome == clean_outcome:
                return route
        raise KeyError(f"no route from {clean_from_node!r} for outcome {clean_outcome!r}")

    def accepts_handoff_artifact(
        self,
        artifact: HandoffArtifact,
        *,
        node_id: PipelineNodeId | str | None = None,
    ) -> bool:
        """Return True when *artifact* matches the selected node's input boundary."""
        if not isinstance(artifact, HandoffArtifact):
            raise TypeError("artifact must be a HandoffArtifact")
        node = self.node(node_id if node_id is not None else self.start_node)
        return artifact.artifact_kind == node.input_artifact_kind


class PipelineRegistry:
    """In-memory registry for provider-neutral pipeline definitions."""

    def __init__(self, pipelines: Iterable[Pipeline] = ()) -> None:
        self._pipelines: dict[PipelineId, Pipeline] = {}
        for pipeline in pipelines:
            self.register(pipeline)

    def register(self, pipeline: Pipeline) -> Self:
        """Register *pipeline*, rejecting duplicate identifiers."""
        if not isinstance(pipeline, Pipeline):
            raise TypeError("pipeline must be a Pipeline")
        key = PipelineId(str(pipeline.id))
        if key in self._pipelines:
            raise ValueError(f"pipeline {key!r} already registered")
        self._pipelines[key] = pipeline
        return self

    def get(self, pipeline_id: PipelineId | str) -> Pipeline:
        """Return a registered pipeline by id."""
        key = PipelineId(_clean_text(pipeline_id, field_name="pipeline_id"))
        try:
            return self._pipelines[key]
        except KeyError as exc:
            raise KeyError(f"unknown pipeline {key!r}") from exc

    def list(self) -> tuple[Pipeline, ...]:
        """Return registered pipelines sorted by id for deterministic callers."""
        return tuple(self._pipelines[key] for key in sorted(self._pipelines))


__all__ = [
    "Pipeline",
    "PipelineExecutionStatus",
    "PipelineId",
    "PipelineNode",
    "PipelineNodeId",
    "PipelineNodeKind",
    "PipelineOutcome",
    "PipelineRegistry",
    "PipelineRoute",
    "ReviewCheckpoint",
]
