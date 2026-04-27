"""Provider-neutral sub-agent domain primitive.

Sub-agents are bounded, composable roles with typed handoff artifacts and
RT-002 progress events. They intentionally carry no provider SDK types or
execution runtime coupling.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, NewType, Self

SubAgentId = NewType("SubAgentId", str)
SubAgentProgressMilestone = Literal[
    "sub_agent_registered",
    "sub_agent_started",
    "sub_agent_completed",
]
SubAgentProgressStatus = Literal["registered", "running", "completed"]

_OPAQUE_PERSONA_PHRASES: tuple[str, ...] = (
    "autonomous coding persona",
    "general autonomous",
    "unconstrained assistant",
    "do whatever is needed",
    "anything necessary",
)


def _clean_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _clean_tuple(values: Iterable[str], *, field_name: str, required: bool) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{field_name} must be an iterable of strings, not a string")
    cleaned = tuple(_clean_text(value, field_name=field_name) for value in values)
    if required and not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    if len(set(cleaned)) != len(cleaned):
        raise ValueError(f"{field_name} must not contain duplicates")
    return cleaned


def _reject_opaque_persona(*values: str) -> None:
    haystack = " ".join(values).lower()
    if any(phrase in haystack for phrase in _OPAQUE_PERSONA_PHRASES):
        raise ValueError("sub-agent must define a bounded role, not an opaque persona")


@dataclass(frozen=True, slots=True)
class SubAgentRole:
    """Explicit role contract for a sub-agent.

    The required fields force the caller to state what the specialist owns,
    what it must not do, and what typed outputs it is expected to produce.
    """

    name: str
    objective: str
    responsibilities: tuple[str, ...]
    constraints: tuple[str, ...]
    non_goals: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = _clean_text(self.name, field_name="name")
        objective = _clean_text(self.objective, field_name="objective")
        responsibilities = _clean_tuple(
            self.responsibilities, field_name="responsibilities", required=True
        )
        constraints = _clean_tuple(self.constraints, field_name="constraints", required=True)
        non_goals = _clean_tuple(self.non_goals, field_name="non_goals", required=False)
        allowed_tools = _clean_tuple(self.allowed_tools, field_name="allowed_tools", required=False)
        expected_outputs = _clean_tuple(
            self.expected_outputs, field_name="expected_outputs", required=True
        )
        _reject_opaque_persona(name, objective, *responsibilities)

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "responsibilities", responsibilities)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "non_goals", non_goals)
        object.__setattr__(self, "allowed_tools", allowed_tools)
        object.__setattr__(self, "expected_outputs", expected_outputs)


@dataclass(frozen=True, slots=True)
class SubAgentHandoffArtifact:
    """Typed artifact produced or expected at a sub-agent boundary."""

    artifact_ref: str
    artifact_kind: str
    label: str
    produced_by: SubAgentId | str
    output_name: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        artifact_ref = _clean_text(self.artifact_ref, field_name="artifact_ref")
        if not artifact_ref.startswith("artifact://"):
            raise ValueError("artifact_ref must use the artifact:// scheme")

        object.__setattr__(self, "artifact_ref", artifact_ref)
        object.__setattr__(
            self,
            "artifact_kind",
            _clean_text(self.artifact_kind, field_name="artifact_kind"),
        )
        object.__setattr__(self, "label", _clean_text(self.label, field_name="label"))
        object.__setattr__(
            self,
            "produced_by",
            SubAgentId(_clean_text(self.produced_by, field_name="produced_by")),
        )
        object.__setattr__(
            self,
            "output_name",
            _clean_text(self.output_name, field_name="output_name"),
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class SubAgent:
    """Bounded specialist role plus typed handoff artifacts."""

    id: SubAgentId | str
    role: SubAgentRole
    handoff_artifacts: tuple[SubAgentHandoffArtifact, ...] = ()

    def __post_init__(self) -> None:
        sub_agent_id = SubAgentId(_clean_text(self.id, field_name="id"))
        object.__setattr__(self, "id", sub_agent_id)

        if not isinstance(self.role, SubAgentRole):
            raise TypeError("role must be a SubAgentRole")

        artifacts = tuple(self.handoff_artifacts)
        for artifact in artifacts:
            if not isinstance(artifact, SubAgentHandoffArtifact):
                raise TypeError("handoff_artifacts must contain SubAgentHandoffArtifact values")
            if artifact.produced_by != sub_agent_id:
                raise ValueError("handoff artifact produced_by must match sub-agent id")
            if artifact.output_name not in self.role.expected_outputs:
                raise ValueError("handoff artifact output_name must be in role.expected_outputs")
        object.__setattr__(self, "handoff_artifacts", artifacts)


class SubAgentRegistry:
    """In-memory registry for provider-neutral sub-agent definitions."""

    def __init__(self, agents: Iterable[SubAgent] = ()) -> None:
        self._agents: dict[SubAgentId, SubAgent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: SubAgent) -> Self:
        """Register *agent*, rejecting duplicate identifiers."""
        if not isinstance(agent, SubAgent):
            raise TypeError("agent must be a SubAgent")
        key = SubAgentId(str(agent.id))
        if key in self._agents:
            raise ValueError(f"sub-agent {key!r} already registered")
        self._agents[key] = agent
        return self

    def get(self, agent_id: SubAgentId | str) -> SubAgent:
        """Return a registered sub-agent by id."""
        key = SubAgentId(_clean_text(agent_id, field_name="agent_id"))
        try:
            return self._agents[key]
        except KeyError as exc:
            raise KeyError(f"unknown sub-agent {key!r}") from exc

    def list(self) -> tuple[SubAgent, ...]:
        """Return registered sub-agents sorted by id for deterministic callers."""
        return tuple(self._agents[key] for key in sorted(self._agents))


__all__ = [
    "SubAgent",
    "SubAgentHandoffArtifact",
    "SubAgentId",
    "SubAgentProgressMilestone",
    "SubAgentProgressStatus",
    "SubAgentRegistry",
    "SubAgentRole",
]
