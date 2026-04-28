"""P7 team + pipeline + adversarial-review end-to-end integration test.

This is the P7 exit-gate test for issue #108. It composes the existing
dispatcher workflow packaging, team primitive, pipeline primitive,
per-agent RT-002 progress, adversarial-review fixture set, and the P6
till-done routine against Postgres.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command as alembic_command
from waywarden.adapters.model.anthropic import AnthropicModelProvider
from waywarden.adapters.model.router import ModelRouter
from waywarden.assets.loader import AssetRegistry
from waywarden.assets.schema import PipelineMetadata, TeamMetadata, WorkflowMetadata
from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import InstanceId, RunId, SessionId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkAllowRule, NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolDecisionRule, ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.domain.pipeline import Pipeline, PipelineNode, PipelineRoute, ReviewCheckpoint
from waywarden.domain.providers import ModelProvider
from waywarden.domain.providers.types.model import PromptEnvelope
from waywarden.domain.run import Run
from waywarden.domain.run_event import RunEvent
from waywarden.domain.subagent import SubAgent, SubAgentRole
from waywarden.domain.team import Team, TeamHandoffRoute
from waywarden.infra.db.repositories.approval_repo import ApprovalRepositoryImpl
from waywarden.infra.db.repositories.run_event_repo import RunEventRepositoryImpl
from waywarden.infra.db.repositories.run_repo import RunRepositoryImpl
from waywarden.infra.db.repositories.token_usage_repo import TokenUsageRepositoryImpl
from waywarden.infra.db.repositories.workspace_manifest_repo import (
    WorkspaceManifestRepositoryImpl,
)
from waywarden.services.approval_engine import ApprovalEngine
from waywarden.services.orchestration.adversarial_review import (
    AdversarialReviewInput,
    AdversarialReviewRoutine,
)
from waywarden.services.orchestration.dispatcher_workflow import DispatcherWorkflowPackager
from waywarden.services.orchestration.handoff_events import make_handoff_artifact_event
from waywarden.services.orchestration.pipeline import PipelineExecutionEngine
from waywarden.services.orchestration.subagent_progress import make_sub_agent_progress_event
from waywarden.services.orchestration.team_progress import make_team_progress_event
from waywarden.services.orchestration.tilldone import (
    IterationResult,
    LoopConfig,
    LoopOutcome,
    _EventStream,
    run_till_done,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "assets"
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ANTHROPIC_CASSETTE = (
    REPO_ROOT / "tests" / "adapters" / "model" / "cassettes" / "anthropic_roundtrip.json"
)
DATABASE_URL = "postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden_dev"


class CassetteMessages:
    """Recorded Anthropic Messages API surface used by the real adapter."""

    def __init__(self, payload: Mapping[str, object]) -> None:
        self.payload = dict(payload)
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> Mapping[str, object]:
        self.calls.append(dict(kwargs))
        return self.payload


class CassetteClient:
    """Minimal client shape accepted by ``AnthropicModelProvider``."""

    def __init__(self, payload: Mapping[str, object]) -> None:
        self.messages = CassetteMessages(payload)


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    db_engine = create_async_engine(DATABASE_URL, echo=False)
    yield db_engine
    await db_engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def apply_migrations(engine: AsyncEngine) -> None:
    previous_database_url = os.environ.get("WAYWARDEN_DATABASE_URL")
    try:
        os.environ["WAYWARDEN_DATABASE_URL"] = DATABASE_URL
        alembic_cfg = AlembicConfig(str(ALEMBIC_INI))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        alembic_command.upgrade(alembic_cfg, "head")
    except OperationalError as exc:
        pytest.skip(f"Postgres unavailable: {exc}")
    finally:
        if previous_database_url is None:
            os.environ.pop("WAYWARDEN_DATABASE_URL", None)
        else:
            os.environ["WAYWARDEN_DATABASE_URL"] = previous_database_url


@pytest_asyncio.fixture
async def session_factory(
    engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def asset_registry() -> AssetRegistry:
    registry = AssetRegistry()
    await registry.load_from_dir(ASSETS_DIR)
    return registry


def _make_run(run_id: str, *, profile: str = "coding") -> Run:
    now = datetime.now(UTC)
    return Run(
        id=RunId(run_id),
        instance_id=InstanceId("inst-p7-e2e"),
        task_id=None,
        profile=profile,
        policy_preset="ask",
        manifest_ref=f"manifest://{run_id}/default",
        entrypoint="internal",
        state="created",
        created_at=now,
        updated_at=now,
        terminal_seq=None,
    )


def _make_manifest(run_id: str) -> WorkspaceManifest:
    return WorkspaceManifest(
        run_id=RunId(run_id),
        inputs=[
            InputMount(
                name="sample-repo",
                kind="directory",
                source_ref="artifact://workspace/sample_repo",
                target_path=str(REPO_ROOT / "tests" / "fixtures" / "sample_repo"),
                read_only=True,
                required=True,
                description="Sample coding repository",
            )
        ],
        writable_paths=[
            WritablePath(
                path="/workspace/run",
                purpose="task-scratch",
                retention="ephemeral",
            )
        ],
        outputs=[
            OutputContract(
                name="plan",
                path="/workspace/output/plan.md",
                kind="file",
                required=True,
                promote_to_artifact=True,
            ),
            OutputContract(
                name="patch",
                path="/workspace/output/patch.diff",
                kind="patch-set",
                required=True,
                promote_to_artifact=True,
            ),
            OutputContract(
                name="review",
                path="/workspace/output/review.json",
                kind="json",
                required=False,
                promote_to_artifact=True,
            ),
        ],
        network_policy=NetworkPolicy(
            mode="allowlist",
            allow=[
                NetworkAllowRule(
                    host_pattern="api.anthropic.com",
                    scheme="https",
                    purpose="model provider",
                )
            ],
            deny=[],
        ),
        tool_policy=ToolPolicy(
            preset="ask",
            default_decision="approval-required",
            rules=[
                ToolDecisionRule(tool="shell", action="read", decision="auto-allow"),
                ToolDecisionRule(tool="adversarial_review", action="clean", decision="auto-allow"),
            ],
        ),
        secret_scope=SecretScope(
            mode="brokered",
            allowed_secret_refs=["secret://anthropic/api-key"],
            mount_env=["ANTHROPIC_API_KEY"],
            redaction_level="full",
        ),
        snapshot_policy=SnapshotPolicy(
            on_start=False,
            on_completion=True,
            on_failure=True,
            before_destructive_actions=True,
            max_snapshots=5,
            include_paths=["/workspace/output"],
            exclude_paths=[],
        ),
    )


def _sub_agent(agent_id: str) -> SubAgent:
    expected_outputs_by_id = {
        "agent-dispatcher": ("team-handoff", "needs-review", "needs-tests"),
        "agent-reviewer": ("review-report",),
        "agent-tester": ("test-report",),
    }
    objectives_by_id = {
        "agent-dispatcher": "Route coding work to bounded specialists.",
        "agent-reviewer": "Review implementation artifacts for defects.",
        "agent-tester": "Exercise issue-scoped tests for the handoff.",
    }
    return SubAgent(
        id=agent_id,
        role=SubAgentRole(
            name=agent_id.removeprefix("agent-"),
            objective=objectives_by_id[agent_id],
            responsibilities=(f"produce {expected_outputs_by_id[agent_id][0]}",),
            constraints=("stay within the typed handoff boundary",),
            expected_outputs=expected_outputs_by_id[agent_id],
        ),
    )


def _team_from_metadata(metadata: TeamMetadata) -> Team:
    return Team(
        id=metadata.id,
        input_artifact_kind=metadata.input_artifact_kind,
        output_artifact_kind=metadata.output_artifact_kind,
        dispatcher=_sub_agent(metadata.dispatcher),
        specialists=tuple(_sub_agent(agent_id) for agent_id in metadata.specialists),
        handoff_routes=tuple(
            TeamHandoffRoute(
                from_agent=route["from_agent"],
                output_name=route["output_name"],
                to_agent=route["to_agent"],
                artifact_kind=route["artifact_kind"],
            )
            for route in metadata.handoff_routes
        ),
        fallback_agent=metadata.fallback_agent,
    )


def _pipeline_from_metadata(metadata: PipelineMetadata) -> Pipeline:
    nodes: list[PipelineNode] = []
    for node in metadata.nodes:
        checkpoint: ReviewCheckpoint | None = None
        if node["kind"] == "review_checkpoint":
            checkpoint_data = cast(dict[str, str], node["review_checkpoint"])
            checkpoint = ReviewCheckpoint(
                input_artifact_kind=checkpoint_data["input_artifact_kind"],
                passed_output_artifact_kind=checkpoint_data["passed_output_artifact_kind"],
                failed_output_artifact_kind=checkpoint_data["failed_output_artifact_kind"],
            )
        nodes.append(
            PipelineNode(
                id=cast(str, node["id"]),
                kind=cast(Any, node["kind"]),
                ref_id=cast(str, node["ref_id"]),
                input_artifact_kind=cast(str, node["input_artifact_kind"]),
                output_artifact_kind=cast(str, node["output_artifact_kind"]),
                phase=cast(Any, node["phase"]),
                milestone=cast(str, node["milestone"]),
                review_checkpoint=checkpoint,
            )
        )
    return Pipeline(
        id=metadata.id,
        start_node=metadata.start_node,
        nodes=tuple(nodes),
        routes=tuple(
            PipelineRoute(
                from_node=cast(str, route["from_node"]),
                outcome=cast(Any, route["outcome"]),
                to_node=route["to_node"],
            )
            for route in metadata.routes
        ),
    )


def _load_fixture(mode: str) -> Mapping[str, object]:
    path = next((REPO_ROOT / "tests" / "fixtures" / "adversarial" / mode).glob("*.json"))
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return cast(Mapping[str, object], loaded)


def _review_input(
    *,
    run_id: str,
    fixture: Mapping[str, object],
    handoff_ref: str,
) -> AdversarialReviewInput:
    input_data = cast(Mapping[str, object], fixture["input"])
    return AdversarialReviewInput(
        run_id=run_id,
        pipeline_id="coding-review-pipeline",
        node_id="review-gate",
        input_artifact_ref=handoff_ref,
        input_artifact_kind="team-handoff",
        handback_text=cast(str, input_data.get("handback_text", "")),
        tool_calls=tuple(cast(Sequence[Mapping[str, object]], input_data.get("tool_calls", ()))),
        memory_items=tuple(
            cast(Sequence[Mapping[str, object]], input_data.get("memory_items", ()))
        ),
        knowledge_items=tuple(
            cast(Sequence[Mapping[str, object]], input_data.get("knowledge_items", ()))
        ),
    )


async def _append_all(
    event_repo: RunEventRepositoryImpl,
    events: Sequence[RunEvent],
) -> list[RunEvent]:
    persisted: list[RunEvent] = []
    for event in events:
        persisted.append(await event_repo.append(event))
    return persisted


def _passing_iteration(iteration_num: int) -> IterationResult:
    return IterationResult(
        plan_artifact_id=f"artifact://p7-e2e/plan-v{iteration_num}",
        check_passed=True,
        changes_applied=True,
        plan_revised=False,
        iteration_count=iteration_num,
        plan_body="Plan: produce a typed handback and run adversarial review.",
        plan_diff_from_previous="",
        plan_rationale="Clean control path for handback.",
    )


def _anthropic_provider_from_cassette() -> tuple[AnthropicModelProvider, CassetteClient]:
    payload = cast(Mapping[str, object], json.loads(ANTHROPIC_CASSETTE.read_text(encoding="utf-8")))
    client = CassetteClient(payload)
    provider = AnthropicModelProvider(api_key="cassette-key", client=cast(Any, client))
    return provider, client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p7_dispatcher_team_pipeline_adversarial_review_e2e(
    session_factory: async_sessionmaker[AsyncSession],
    asset_registry: AssetRegistry,
) -> None:
    run_suffix = uuid4().hex
    dispatcher_run_id = f"run-p7-dispatcher-{run_suffix}"
    team_run_id = f"run-p7-team-{run_suffix}"
    pipeline_run_id = f"run-p7-pipeline-{run_suffix}"
    review_run_id = f"run-p7-review-{run_suffix}"
    sub_agent_run_id = f"run-p7-reviewer-{run_suffix}"
    clean_run_id = f"run-p7-clean-{run_suffix}"
    destructive_run_id = f"run-p7-destructive-{run_suffix}"
    till_done_run_id = f"run-p7-tilldone-{run_suffix}"

    workflow = cast(WorkflowMetadata, asset_registry.get("coding-dispatcher-workflow", "workflow"))
    team = _team_from_metadata(
        cast(TeamMetadata, asset_registry.get("coding-dispatch-team", "team"))
    )
    pipeline = _pipeline_from_metadata(
        cast(PipelineMetadata, asset_registry.get("coding-review-pipeline", "pipeline"))
    )
    parent_manifest = _make_manifest(dispatcher_run_id)
    correlation = RunCorrelation(
        correlation_id=f"corr-p7-{run_suffix}",
        parent_run_id=dispatcher_run_id,
        child_run_id=team_run_id,
        dispatcher_run_id=dispatcher_run_id,
        team_run_id=team_run_id,
        pipeline_run_id=pipeline_run_id,
        review_run_id=review_run_id,
        sub_agent_run_id=sub_agent_run_id,
        delegation_id=f"del-{dispatcher_run_id}-1",
        manifest_run_id=team_run_id,
    )
    now = datetime(2026, 4, 28, tzinfo=UTC)

    async with session_factory() as session:
        run_repo = RunRepositoryImpl(session)
        manifest_repo = WorkspaceManifestRepositoryImpl(session)
        for run_id in (
            dispatcher_run_id,
            team_run_id,
            pipeline_run_id,
            review_run_id,
            sub_agent_run_id,
            clean_run_id,
            destructive_run_id,
            till_done_run_id,
        ):
            await run_repo.create(_make_run(run_id))
        await manifest_repo.save(parent_manifest)
        await session.commit()

    package = DispatcherWorkflowPackager(now=lambda: now).package(
        workflow=workflow,
        parent_manifest=parent_manifest,
        objective="Run a coding handback through team, pipeline, and adversarial review.",
        correlation=correlation,
        artifact_ref=f"artifact://runs/{dispatcher_run_id}/team-handoff",
    )

    assert team.accepts_handoff_artifact(package.handoff_artifact)
    assert pipeline.accepts_handoff_artifact(package.handoff_artifact, node_id="team-run")
    assert pipeline.accepts_handoff_artifact(package.handoff_artifact, node_id="review-gate")

    team_event = make_team_progress_event(
        run_id=RunId(team_run_id),
        team=team,
        seq=1,
        milestone="team_started",
        status="running",
        summary="Coding dispatch team started.",
        member_statuses={
            "agent-dispatcher": "completed",
            "agent-reviewer": "running",
            "agent-tester": "registered",
        },
        member_run_ids={
            "agent-dispatcher": dispatcher_run_id,
            "agent-reviewer": sub_agent_run_id,
            "agent-tester": f"run-p7-tester-{run_suffix}",
        },
        correlation=correlation,
        now=now,
    )
    sub_agent_events = (
        make_sub_agent_progress_event(
            run_id=RunId(team_run_id),
            sub_agent=team.dispatcher,
            seq=2,
            milestone="sub_agent_completed",
            status="completed",
            summary="Dispatcher emitted typed team handoff.",
            correlation=correlation,
            now=now,
        ),
        make_sub_agent_progress_event(
            run_id=RunId(team_run_id),
            sub_agent=team.specialists[0],
            seq=3,
            milestone="sub_agent_started",
            status="running",
            summary="Reviewer started bounded review.",
            correlation=correlation,
            now=now,
        ),
        make_sub_agent_progress_event(
            run_id=RunId(team_run_id),
            sub_agent=team.specialists[1],
            seq=4,
            milestone="sub_agent_started",
            status="running",
            summary="Tester started issue-scoped validation.",
            correlation=correlation,
            now=now,
        ),
    )
    team_to_pipeline_artifact = make_handoff_artifact_event(
        run_id=RunId(team_run_id),
        handoff_artifact=package.handoff_artifact,
        seq=5,
        source_run_id=team_run_id,
        target_run_id=pipeline_run_id,
        handoff_boundary="team_to_pipeline",
        correlation=correlation,
        source_agent_id=str(team.dispatcher.id),
        target_agent_id=str(team.specialists[0].id),
        now=now,
    )
    pipeline_result = PipelineExecutionEngine(now=lambda: now).execute(
        pipeline=pipeline,
        run_id=RunId(pipeline_run_id),
        outcomes={"team-run": "success", "review-gate": "success"},
        correlation=correlation,
    )

    async with session_factory() as session:
        event_repo = RunEventRepositoryImpl(session)
        persisted_dispatcher_events = await _append_all(
            event_repo,
            (package.progress_event, package.artifact_event),
        )
        persisted_team_events = await _append_all(
            event_repo,
            (team_event, *sub_agent_events, team_to_pipeline_artifact),
        )
        persisted_pipeline_events = await _append_all(event_repo, pipeline_result.events)
        await session.commit()

    async with session_factory() as session:
        event_repo = RunEventRepositoryImpl(session)
        approval_engine = ApprovalEngine(
            approvals=ApprovalRepositoryImpl(session),
            events=event_repo,
        )
        review = AdversarialReviewRoutine(
            approval_engine=approval_engine,
            tool_policy=parent_manifest.tool_policy,
            now=lambda: now,
        )
        prompt_injection_result = await review.review(
            _review_input(
                run_id=review_run_id,
                fixture=_load_fixture("prompt_injection"),
                handoff_ref=package.handoff_artifact.artifact_ref,
            )
        )
        clean_result = await review.review(
            _review_input(
                run_id=clean_run_id,
                fixture=_load_fixture("control"),
                handoff_ref=package.handoff_artifact.artifact_ref,
            )
        )
        destructive_result = await review.review(
            _review_input(
                run_id=destructive_run_id,
                fixture=_load_fixture("destructive_tool_misuse"),
                handoff_ref=package.handoff_artifact.artifact_ref,
            )
        )
        await session.commit()

    till_done_stream = _EventStream()
    till_done_outcome = await run_till_done(
        till_done_run_id,
        iteration_result_fn=_passing_iteration,
        config=LoopConfig(max_iterations=3, check_failure_max=2),
        events=till_done_stream,
    )

    provider, client = _anthropic_provider_from_cassette()
    assert isinstance(provider, ModelProvider)
    async with session_factory() as session:
        router = ModelRouter(
            providers={"anthropic": provider},
            default="anthropic",
            token_usage_repository=TokenUsageRepositoryImpl(session),
        )
        completion = await router.complete(
            PromptEnvelope(
                session_id=SessionId(clean_run_id),
                messages=["Return the recorded handback summary."],
                system_prompt="You are the coding handback summarizer.",
            ),
            run_id=clean_run_id,
            call_ref="p7-e2e-clean-handback",
        )
        token_usage = await TokenUsageRepositoryImpl(session).list(clean_run_id)
        await session.commit()

    async with session_factory() as session:
        event_repo = RunEventRepositoryImpl(session)
        dispatcher_events = await event_repo.list(dispatcher_run_id)
        team_events = await event_repo.list(team_run_id)
        pipeline_events = await event_repo.list(pipeline_run_id)
        review_events = await event_repo.list(review_run_id)
        clean_events = await event_repo.list(clean_run_id)
        destructive_events = await event_repo.list(destructive_run_id)

    assert [event.seq for event in dispatcher_events] == [1, 2]
    assert dispatcher_events[1].payload["artifact_ref"] == package.handoff_artifact.artifact_ref
    assert dispatcher_events[1].payload["handoff_boundary"] == "dispatcher_to_team"
    assert dispatcher_events[1].payload["correlation_id"] == correlation.correlation_id

    assert [event.seq for event in team_events] == [1, 2, 3, 4, 5]
    per_agent_progress = [
        event
        for event in team_events
        if event.type == "run.progress" and "sub_agent_id" in event.payload
    ]
    assert [event.payload["sub_agent_id"] for event in per_agent_progress] == [
        "agent-dispatcher",
        "agent-reviewer",
        "agent-tester",
    ]
    assert all(
        event.payload["correlation_id"] == correlation.correlation_id for event in team_events
    )
    assert team_events[4].payload["handoff_boundary"] == "team_to_pipeline"

    assert pipeline_result.status == "completed"
    assert pipeline_result.visited_node_ids == ("team-run", "review-gate")
    assert persisted_pipeline_events[1].payload["node_id"] == "review-gate"
    assert [event.seq for event in pipeline_events] == [1, 2]
    assert pipeline_events[1].payload["correlation_id"] == correlation.correlation_id

    assert prompt_injection_result.gate_decision == "branch"
    assert prompt_injection_result.pipeline_outcome == "failure"
    assert prompt_injection_result.findings[0].finding_class == "prompt_injection"
    assert review_events[-1].payload["finding_class"] == "prompt_injection"
    assert review_events[-1].payload["gate_decision"] == "branch"

    assert destructive_result.gate_decision == "abort"
    assert destructive_result.status == "aborted"
    assert destructive_result.pipeline_outcome == "failure"
    assert destructive_events[-1].payload["finding_class"] == "destructive_tool_misuse"
    assert destructive_events[-1].payload["gate_decision"] == "abort"

    assert clean_result.findings == ()
    assert clean_result.gate_decision == "continue"
    assert clean_result.pipeline_outcome == "success"
    assert len(clean_events) == 1
    assert clean_events[0].payload["finding_class"] == "none"
    assert clean_events[0].payload["gate_decision"] == "continue"

    assert till_done_outcome == LoopOutcome.COMPLETED
    assert any(
        event.type == "run.progress" and event.payload["milestone"] == "terminal"
        for event in till_done_stream.events
    )
    assert completion.provider == "anthropic"
    assert completion.text == "Cassette response from Anthropic."
    assert token_usage[0].provider == "anthropic"
    assert token_usage[0].call_ref == "p7-e2e-clean-handback"
    assert client.messages.calls[0]["model"] == "claude-3-5-sonnet-latest"

    assert len(persisted_dispatcher_events) == 2
    assert len(persisted_team_events) == 5
    assert len(persisted_pipeline_events) == 2
