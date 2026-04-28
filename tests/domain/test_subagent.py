"""Unit tests for the provider-neutral sub-agent primitive."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import RunId
from waywarden.domain.subagent import (
    SubAgent,
    SubAgentHandoffArtifact,
    SubAgentRegistry,
    SubAgentRole,
)
from waywarden.services.orchestration.milestones import is_valid_milestone
from waywarden.services.orchestration.subagent_progress import make_sub_agent_progress_event


def _role(**overrides: Any) -> SubAgentRole:
    fields: dict[str, Any] = {
        "name": "reviewer",
        "objective": "Review a bounded patch for correctness.",
        "responsibilities": ("inspect diff", "report defects"),
        "constraints": ("do not modify files",),
        "non_goals": ("implementation work",),
        "allowed_tools": ("read_file",),
        "expected_outputs": ("review-report",),
    }
    fields.update(overrides)
    return SubAgentRole(**fields)


def test_sub_agent_role_requires_explicit_bounds() -> None:
    role = _role()

    assert role.name == "reviewer"
    assert role.constraints == ("do not modify files",)
    assert role.non_goals == ("implementation work",)
    assert role.allowed_tools == ("read_file",)
    assert role.expected_outputs == ("review-report",)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("responsibilities", ()),
        ("constraints", ()),
        ("expected_outputs", ()),
    ],
)
def test_sub_agent_role_rejects_missing_required_bounds(field_name: str, value: object) -> None:
    with pytest.raises(ValueError, match=field_name):
        _role(**{field_name: value})


def test_sub_agent_role_rejects_string_for_tuple_bounds() -> None:
    with pytest.raises(TypeError, match="responsibilities"):
        _role(responsibilities="review everything")


@pytest.mark.parametrize(
    "objective",
    [
        "You are a general autonomous coding persona.",
        "Act as an unconstrained assistant and do whatever is needed.",
    ],
)
def test_sub_agent_role_fails_fast_on_opaque_personas(objective: str) -> None:
    with pytest.raises(ValueError, match="bounded role"):
        _role(objective=objective)


def test_sub_agent_is_frozen_and_provider_neutral() -> None:
    agent = SubAgent(
        id="agent-reviewer",
        role=_role(),
        handoff_artifacts=(
            SubAgentHandoffArtifact(
                artifact_ref="artifact://runs/run-1/review-report",
                artifact_kind="review-report",
                label="Review report",
                produced_by="agent-reviewer",
                output_name="review-report",
            ),
        ),
    )

    assert agent.id == "agent-reviewer"
    assert agent.role.name == "reviewer"
    with pytest.raises(FrozenInstanceError):
        cast(Any, agent).id = "agent-other"


def test_handoff_artifact_validation_requires_matching_output() -> None:
    artifact = SubAgentHandoffArtifact(
        artifact_ref="artifact://runs/run-1/review-report",
        artifact_kind="review-report",
        label="Review report",
        produced_by="agent-reviewer",
        output_name="patch",
    )

    with pytest.raises(ValueError, match="expected_outputs"):
        SubAgent(id="agent-reviewer", role=_role(), handoff_artifacts=(artifact,))


@pytest.mark.parametrize(
    ("artifact_ref", "artifact_kind", "label"),
    [
        ("runs/run-1/review-report", "review-report", "Review report"),
        ("artifact://runs/run-1/review-report", "", "Review report"),
        ("artifact://runs/run-1/review-report", "review-report", " "),
    ],
)
def test_handoff_artifact_rejects_malformed_inputs(
    artifact_ref: str, artifact_kind: str, label: str
) -> None:
    with pytest.raises(ValueError):
        SubAgentHandoffArtifact(
            artifact_ref=artifact_ref,
            artifact_kind=artifact_kind,
            label=label,
            produced_by="agent-reviewer",
            output_name="review-report",
        )


def test_sub_agent_registry_registers_and_lists_deterministically() -> None:
    reviewer = SubAgent(id="agent-reviewer", role=_role(name="reviewer"))
    tester = SubAgent(id="agent-tester", role=_role(name="tester"))
    registry = SubAgentRegistry()

    registry.register(tester)
    registry.register(reviewer)

    assert registry.get("agent-reviewer") == reviewer
    assert registry.list() == (reviewer, tester)


def test_sub_agent_registry_rejects_duplicate_ids() -> None:
    registry = SubAgentRegistry()
    registry.register(SubAgent(id="agent-reviewer", role=_role()))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(SubAgent(id="agent-reviewer", role=_role(name="other")))


def test_sub_agent_progress_event_uses_rt002_catalog_milestone() -> None:
    agent = SubAgent(id="agent-reviewer", role=_role())
    correlation = RunCorrelation(
        correlation_id="corr-review-1",
        parent_run_id="run-parent",
        child_run_id="run-child",
        dispatcher_run_id="run-parent",
        team_run_id="run-team",
        pipeline_run_id="run-pipeline",
        delegation_id="del-run-parent-1",
        manifest_run_id="run-child",
        sub_agent_run_id="run-child",
    )
    event = make_sub_agent_progress_event(
        run_id=RunId("run-child"),
        sub_agent=agent,
        seq=1,
        milestone="sub_agent_started",
        status="running",
        summary="Reviewer started",
        now=datetime(2026, 4, 27, tzinfo=UTC),
        correlation=correlation,
    )

    assert event.type == "run.progress"
    assert event.payload["phase"] == "handoff"
    assert event.payload["milestone"] == "sub_agent_started"
    assert event.payload["milestone_ref"] == "handoff.sub_agent_started"
    assert event.payload["run_id"] == "run-child"
    assert event.payload["agent_id"] == "agent-reviewer"
    assert event.payload["parent_run_id"] == "run-parent"
    assert event.payload["sub_agent_id"] == "agent-reviewer"
    assert event.payload["role"] == "reviewer"
    assert is_valid_milestone(str(event.payload["phase"]), str(event.payload["milestone"]))
