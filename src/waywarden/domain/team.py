"""Provider-neutral team domain primitive.

Teams compose bounded sub-agents behind an explicit dispatcher and typed
handoff routes. They intentionally carry no provider SDK types or runtime
adapter coupling.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, NewType, Self, cast

from waywarden.domain.subagent import (
    SubAgent,
    SubAgentId,
    SubAgentProgressStatus,
)

TeamId = NewType("TeamId", str)
TeamProgressMilestone = Literal["team_started", "team_completed", "team_blocked"]
TeamProgressStatus = Literal["running", "completed", "blocked"]


def _clean_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


@dataclass(frozen=True, slots=True)
class TeamHandoffRoute:
    """Typed route from one team member's output to another team member."""

    from_agent: SubAgentId | str
    output_name: str
    to_agent: SubAgentId | str
    artifact_kind: str
    is_fallback: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "from_agent",
            SubAgentId(_clean_text(self.from_agent, field_name="from_agent")),
        )
        object.__setattr__(
            self,
            "output_name",
            _clean_text(self.output_name, field_name="output_name"),
        )
        object.__setattr__(
            self,
            "to_agent",
            SubAgentId(_clean_text(self.to_agent, field_name="to_agent")),
        )
        object.__setattr__(
            self,
            "artifact_kind",
            _clean_text(self.artifact_kind, field_name="artifact_kind"),
        )


@dataclass(frozen=True, slots=True)
class Team:
    """Dispatcher plus specialist sub-agents with typed handoff routing."""

    id: TeamId | str
    dispatcher: SubAgent
    specialists: tuple[SubAgent, ...]
    handoff_routes: tuple[TeamHandoffRoute, ...] = ()
    fallback_agent: SubAgentId | str | None = None
    provider_config: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        team_id = TeamId(_clean_text(self.id, field_name="id"))
        object.__setattr__(self, "id", team_id)

        if not isinstance(self.dispatcher, SubAgent):
            raise TypeError("dispatcher must be a SubAgent")

        specialists = tuple(self.specialists)
        if not specialists:
            raise ValueError("specialists must not be empty")
        if any(not isinstance(agent, SubAgent) for agent in specialists):
            raise TypeError("specialists must contain SubAgent values")

        members = (self.dispatcher, *specialists)
        member_by_id: dict[SubAgentId, SubAgent] = {}
        for member in members:
            member_id = cast(SubAgentId, member.id)
            if member_id in member_by_id:
                raise ValueError(f"duplicate team member {member_id!r}")
            member_by_id[member_id] = member

        routes = tuple(self.handoff_routes)
        for route in routes:
            if not isinstance(route, TeamHandoffRoute):
                raise TypeError("handoff_routes must contain TeamHandoffRoute values")
            from_agent = cast(SubAgentId, route.from_agent)
            to_agent = cast(SubAgentId, route.to_agent)
            if from_agent not in member_by_id:
                raise ValueError(f"handoff route references unknown from_agent {from_agent!r}")
            if to_agent not in member_by_id:
                raise ValueError(f"handoff route references unknown to_agent {to_agent!r}")
            if from_agent == to_agent:
                raise ValueError("handoff route cannot target the same agent")
            source = member_by_id[from_agent]
            if route.output_name not in source.role.expected_outputs:
                raise ValueError("handoff route output_name must be in source expected_outputs")

        fallback_agent = self.fallback_agent
        if fallback_agent is not None:
            fallback_agent = SubAgentId(_clean_text(fallback_agent, field_name="fallback_agent"))
            specialist_ids = {agent.id for agent in specialists}
            if fallback_agent not in specialist_ids:
                raise ValueError("fallback_agent must reference a specialist")

        self._raise_on_deadlock(routes)

        if self.provider_config:
            raise ValueError(
                "team provider_config must be empty; provider behavior belongs to adapters"
            )

        object.__setattr__(self, "specialists", specialists)
        object.__setattr__(self, "handoff_routes", routes)
        object.__setattr__(self, "fallback_agent", fallback_agent)
        object.__setattr__(self, "provider_config", MappingProxyType({}))

    @property
    def member_ids(self) -> tuple[str, ...]:
        """Return dispatcher first, then specialists, as stable string IDs."""
        return tuple(str(agent.id) for agent in (self.dispatcher, *self.specialists))

    def route_handoff(self, from_agent: SubAgentId | str, output_name: str) -> TeamHandoffRoute:
        """Return the typed route for a handoff, using dispatcher fallback when configured."""
        clean_from_agent = SubAgentId(_clean_text(from_agent, field_name="from_agent"))
        clean_output_name = _clean_text(output_name, field_name="output_name")
        member_ids = {SubAgentId(member_id) for member_id in self.member_ids}
        if clean_from_agent not in member_ids:
            raise KeyError(f"unknown team member {clean_from_agent!r}")

        for route in self.handoff_routes:
            if route.from_agent == clean_from_agent and route.output_name == clean_output_name:
                return route

        if clean_from_agent == self.dispatcher.id and self.fallback_agent is not None:
            return TeamHandoffRoute(
                from_agent=clean_from_agent,
                output_name=clean_output_name,
                to_agent=self.fallback_agent,
                artifact_kind="team-fallback-handoff",
                is_fallback=True,
            )

        raise KeyError(
            f"no handoff route from {clean_from_agent!r} for output {clean_output_name!r}"
        )

    @staticmethod
    def _raise_on_deadlock(routes: tuple[TeamHandoffRoute, ...]) -> None:
        graph: dict[SubAgentId, set[SubAgentId]] = {}
        for route in routes:
            from_agent = cast(SubAgentId, route.from_agent)
            to_agent = cast(SubAgentId, route.to_agent)
            graph.setdefault(from_agent, set()).add(to_agent)

        visiting: set[SubAgentId] = set()
        visited: set[SubAgentId] = set()

        def visit(node: SubAgentId) -> None:
            if node in visiting:
                raise ValueError("team handoff routes contain a deadlock cycle")
            if node in visited:
                return
            visiting.add(node)
            for target in graph.get(node, set()):
                visit(target)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)


class TeamRegistry:
    """In-memory registry for provider-neutral team definitions."""

    def __init__(self, teams: Iterable[Team] = ()) -> None:
        self._teams: dict[TeamId, Team] = {}
        for team in teams:
            self.register(team)

    def register(self, team: Team) -> Self:
        """Register *team*, rejecting duplicate identifiers."""
        if not isinstance(team, Team):
            raise TypeError("team must be a Team")
        key = TeamId(str(team.id))
        if key in self._teams:
            raise ValueError(f"team {key!r} already registered")
        self._teams[key] = team
        return self

    def get(self, team_id: TeamId | str) -> Team:
        """Return a registered team by id."""
        key = TeamId(_clean_text(team_id, field_name="team_id"))
        try:
            return self._teams[key]
        except KeyError as exc:
            raise KeyError(f"unknown team {key!r}") from exc

    def list(self) -> tuple[Team, ...]:
        """Return registered teams sorted by id for deterministic callers."""
        return tuple(self._teams[key] for key in sorted(self._teams))


TeamMemberProgressStatus = SubAgentProgressStatus

__all__ = [
    "Team",
    "TeamHandoffRoute",
    "TeamId",
    "TeamMemberProgressStatus",
    "TeamProgressMilestone",
    "TeamProgressStatus",
    "TeamRegistry",
]
