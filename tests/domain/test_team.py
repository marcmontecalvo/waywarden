"""Unit tests for the provider-neutral team primitive."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from waywarden.domain.subagent import SubAgent, SubAgentRole
from waywarden.domain.team import Team, TeamHandoffRoute, TeamRegistry


def _agent(agent_id: str, name: str, outputs: tuple[str, ...]) -> SubAgent:
    return SubAgent(
        id=agent_id,
        role=SubAgentRole(
            name=name,
            objective=f"Own {name} work inside a bounded team.",
            responsibilities=(f"handle {name} tasks",),
            constraints=("stay inside the assigned team role",),
            non_goals=("own unrelated team roles",),
            allowed_tools=("read_file",),
            expected_outputs=outputs,
        ),
    )


def test_team_routes_dispatcher_to_two_specialists_with_typed_handoffs() -> None:
    dispatcher = _agent("agent-dispatcher", "dispatcher", ("needs-review", "needs-tests"))
    reviewer = _agent("agent-reviewer", "reviewer", ("review-report",))
    tester = _agent("agent-tester", "tester", ("test-report",))

    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=dispatcher,
        specialists=(reviewer, tester),
        handoff_routes=(
            TeamHandoffRoute(
                from_agent="agent-dispatcher",
                output_name="needs-review",
                to_agent="agent-reviewer",
                artifact_kind="review-request",
            ),
            TeamHandoffRoute(
                from_agent="agent-dispatcher",
                output_name="needs-tests",
                to_agent="agent-tester",
                artifact_kind="test-request",
            ),
        ),
        fallback_agent="agent-reviewer",
    )

    assert team.member_ids == ("agent-dispatcher", "agent-reviewer", "agent-tester")
    assert team.route_handoff("agent-dispatcher", "needs-review").to_agent == "agent-reviewer"
    assert team.route_handoff("agent-dispatcher", "needs-tests").to_agent == "agent-tester"


def test_team_dispatcher_fallback_routes_unmatched_handoff_to_fallback_specialist() -> None:
    dispatcher = _agent("agent-dispatcher", "dispatcher", ("needs-review", "needs-tests"))
    reviewer = _agent("agent-reviewer", "reviewer", ("review-report",))
    tester = _agent("agent-tester", "tester", ("test-report",))
    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=dispatcher,
        specialists=(reviewer, tester),
        handoff_routes=(
            TeamHandoffRoute(
                from_agent="agent-dispatcher",
                output_name="needs-review",
                to_agent="agent-reviewer",
                artifact_kind="review-request",
            ),
        ),
        fallback_agent="agent-tester",
    )

    route = team.route_handoff("agent-dispatcher", "needs-tests")

    assert route.to_agent == "agent-tester"
    assert route.is_fallback is True
    assert route.artifact_kind == "team-fallback-handoff"


def test_team_detects_deadlocked_handoff_cycles() -> None:
    dispatcher = _agent("agent-dispatcher", "dispatcher", ("needs-review",))
    reviewer = _agent("agent-reviewer", "reviewer", ("needs-tests",))
    tester = _agent("agent-tester", "tester", ("needs-review",))

    with pytest.raises(ValueError, match="deadlock"):
        Team(
            id="coding-team",
            input_artifact_kind="team-handoff",
            output_artifact_kind="team-handoff",
            dispatcher=dispatcher,
            specialists=(reviewer, tester),
            handoff_routes=(
                TeamHandoffRoute(
                    from_agent="agent-dispatcher",
                    output_name="needs-review",
                    to_agent="agent-reviewer",
                    artifact_kind="review-request",
                ),
                TeamHandoffRoute(
                    from_agent="agent-reviewer",
                    output_name="needs-tests",
                    to_agent="agent-tester",
                    artifact_kind="test-request",
                ),
                TeamHandoffRoute(
                    from_agent="agent-tester",
                    output_name="needs-review",
                    to_agent="agent-reviewer",
                    artifact_kind="review-request",
                ),
            ),
        )


def test_team_rejects_provider_specific_metadata_and_is_frozen() -> None:
    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher", "dispatcher", ("needs-review",)),
        specialists=(_agent("agent-reviewer", "reviewer", ("review-report",)),),
        fallback_agent="agent-reviewer",
    )

    assert team.provider_config == {}
    with pytest.raises(FrozenInstanceError):
        cast(Any, team).id = "other-team"


def test_team_registry_registers_and_lists_deterministically() -> None:
    first = Team(
        id="coding-team-a",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher-a", "dispatcher-a", ("needs-review",)),
        specialists=(_agent("agent-reviewer-a", "reviewer-a", ("review-report",)),),
    )
    second = Team(
        id="coding-team-b",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher-b", "dispatcher-b", ("needs-review",)),
        specialists=(_agent("agent-reviewer-b", "reviewer-b", ("review-report",)),),
    )

    registry = TeamRegistry((second, first))

    assert registry.get("coding-team-a") == first
    assert registry.list() == (first, second)
