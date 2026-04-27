"""EA profile end-to-end integration proof against real Postgres/runtime paths."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
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
from waywarden.adapters.model.fake import FakeModelProvider
from waywarden.adapters.model.router import ModelRouter
from waywarden.adapters.provider_factory import build_knowledge_provider, build_memory_provider
from waywarden.api.routers.run_events import _build_stream
from waywarden.api.streaming.sse import _json_sse_frame
from waywarden.assets.loader import AssetRegistry
from waywarden.config.settings import AppConfig
from waywarden.domain.ids import InstanceId, RunId, SessionId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkAllowRule, NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolDecisionRule, ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.domain.providers.types.memory import MemoryEntry
from waywarden.domain.run import Run
from waywarden.infra.db.repositories.approval_repo import ApprovalRepositoryImpl
from waywarden.infra.db.repositories.run_event_repo import RunEventRepositoryImpl
from waywarden.infra.db.repositories.run_repo import RunRepositoryImpl
from waywarden.infra.db.repositories.task_repo import TaskRepositoryImpl
from waywarden.infra.db.repositories.token_usage_repo import TokenUsageRepositoryImpl
from waywarden.infra.db.repositories.workspace_manifest_repo import (
    WorkspaceManifestRepositoryImpl,
)
from waywarden.profiles.ea.hydrate import hydrate_ea_profile
from waywarden.services.approval_engine import ApprovalEngine
from waywarden.services.approval_types import Granted
from waywarden.services.context_builder import ContextBuilder
from waywarden.services.ea_task_service import EATaskService
from waywarden.services.orchestration.briefing import InboxEntry
from waywarden.services.orchestration.routine import EACoroutine
from waywarden.services.orchestration.scheduler import ScheduledTask
from waywarden.services.orchestration.triage import InboxItem

REPO_ROOT = Path(__file__).resolve().parents[3]
EA_PROFILE_PATH = REPO_ROOT / "profiles" / "ea" / "profile.yaml"
ASSETS_DIR = REPO_ROOT / "assets"
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
DATABASE_URL = "postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden_dev"


@pytest_asyncio.fixture(scope="session")
async def _engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _apply_migrations(_engine: AsyncEngine) -> None:
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
async def session_factory(_engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _make_run(run_id: str) -> Run:
    now = datetime.now(UTC)
    return Run(
        id=RunId(run_id),
        instance_id=InstanceId("inst-ea-e2e"),
        task_id=None,
        profile="ea",
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
                name="repo",
                kind="directory",
                source_ref="artifact://workspace/repo",
                target_path="/workspace/repo",
                read_only=True,
                required=True,
                description="Waywarden checkout",
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
                name="briefing",
                path="/workspace/run/briefing.md",
                kind="report",
                required=True,
                promote_to_artifact=True,
            )
        ],
        network_policy=NetworkPolicy(
            mode="allowlist",
            allow=[
                NetworkAllowRule(
                    host_pattern="api.github.com",
                    scheme="https",
                    purpose="issue metadata",
                )
            ],
            deny=[],
        ),
        tool_policy=ToolPolicy(
            preset="ask",
            default_decision="approval-required",
            rules=[
                ToolDecisionRule(tool="shell", action="read", decision="auto-allow"),
            ],
        ),
        secret_scope=SecretScope(
            mode="brokered",
            allowed_secret_refs=["github.default"],
            mount_env=[],
            redaction_level="full",
        ),
        snapshot_policy=SnapshotPolicy(
            on_start=False,
            on_completion=True,
            on_failure=True,
            before_destructive_actions=True,
            max_snapshots=3,
            include_paths=["/workspace/run"],
            exclude_paths=[],
        ),
    )


async def _load_asset_registry() -> AssetRegistry:
    registry = AssetRegistry()
    await registry.load_from_dir(ASSETS_DIR)
    return registry


async def _collect_replay(
    stream: AsyncGenerator[bytes],
    *,
    expected_count: int,
) -> list[bytes]:
    frames: list[bytes] = []
    async for frame in stream:
        frames.append(frame)
        if len(frames) >= expected_count:
            break
    await stream.aclose()
    return frames


def _provider_config() -> AppConfig:
    return AppConfig(
        host="127.0.0.1",
        port=9999,
        active_profile="ea",
        model_router="fake",
        model_router_default_provider="fake-model",
        memory_provider="fake",
        knowledge_provider="filesystem",
        knowledge_filesystem_root=str(REPO_ROOT / "assets" / "knowledge"),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ea_profile_e2e_roundtrip_via_postgres(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = f"run-ea-e2e-{uuid4().hex}"
    session_id = SessionId(f"ea-session-{uuid4().hex[:8]}")
    manifest = _make_manifest(run_id)
    asset_registry = await _load_asset_registry()
    profile = hydrate_ea_profile(profile_path=EA_PROFILE_PATH, asset_registry=asset_registry)
    resolved_asset_ids = {asset.id for asset in profile.resolved_assets}

    assert {"ea-briefing", "ea-inbox-triage", "ea-scheduler"} <= resolved_asset_ids

    async with session_factory() as session:
        run_repo = RunRepositoryImpl(session)
        task_repo = TaskRepositoryImpl(session)
        approval_repo = ApprovalRepositoryImpl(session)
        event_repo = RunEventRepositoryImpl(session)
        manifest_repo = WorkspaceManifestRepositoryImpl(session)
        token_usage_repo = TokenUsageRepositoryImpl(session)

        await run_repo.create(_make_run(run_id))
        await manifest_repo.save(manifest)

        config = _provider_config()
        memory_provider = build_memory_provider(config.memory_provider, {})
        knowledge_provider = build_knowledge_provider(
            config.knowledge_provider,
            {"knowledge_filesystem_root": config.knowledge_filesystem_root},
        )
        await memory_provider.write(
            session_id,
            MemoryEntry(
                session_id=session_id,
                content="Operator wants the EA to prioritize finance and scheduling work.",
            ),
        )
        context_builder = ContextBuilder.from_config(memory_provider, knowledge_provider, config)
        prompt = await context_builder.build(session_id, "Draft the executive assistant briefing.")
        model_router = ModelRouter(
            providers={
                "fake-model": FakeModelProvider(
                    provider="fake-model",
                    model="fake-model",
                )
            },
            default="fake-model",
            token_usage_repository=token_usage_repo,
        )
        completion = await model_router.complete(
            prompt,
            run_id=run_id,
            call_ref="ea-e2e-briefing",
        )

        assert completion.provider == "fake-model"
        assert completion.model == "fake-model"

        approval_engine = ApprovalEngine(approvals=approval_repo, events=event_repo)
        task_service = EATaskService(
            task_repo=task_repo,
            approval_engine=approval_engine,
            events=event_repo,
        )
        routine_surface = EACoroutine(task_service=task_service, event_repo=event_repo)

        briefing = await routine_surface.execute(
            "ea-briefing",
            profile.resolved_assets,
            run_id=run_id,
            inbox_entries=[
                InboxEntry(
                    subject="Meeting rescheduled",
                    body=f"Use this generated context: {completion.text}",
                    from_address="chief@example.com",
                )
            ],
            pending_tasks=0,
        )
        triage = await routine_surface.execute(
            "ea-inbox-triage",
            profile.resolved_assets,
            run_id=run_id,
            items=[
                InboxItem(
                    subject="Budget review request",
                    from_address="finance@example.com",
                    body="Please prepare the Q4 review pack.",
                )
            ],
            decisions={"Budget review request": Granted()},
        )
        scheduler = await routine_surface.execute(
            "ea-scheduler",
            profile.resolved_assets,
            run_id=run_id,
            tasks=[
                ScheduledTask(
                    title="Prepare Q4 budget",
                    objective="Gather finance data and draft the report.",
                )
            ],
        )

        await session.commit()

    assert briefing.state.inbox_received == 1
    assert triage.items_triaged == 1
    assert triage.items_approved == 1
    assert scheduler.tasks_processed == 1
    assert scheduler.tasks_approved == 0

    async with session_factory() as read_session:
        event_repo = RunEventRepositoryImpl(read_session)
        manifest_repo = WorkspaceManifestRepositoryImpl(read_session)
        token_usage_repo = TokenUsageRepositoryImpl(read_session)

        reloaded_manifest = await manifest_repo.get(run_id)
        assert reloaded_manifest == manifest

        usage_entries = await token_usage_repo.list(run_id)
        assert len(usage_entries) == 1
        assert usage_entries[0].provider == "fake-model"
        assert usage_entries[0].model == "fake-model"

        history = await event_repo.list(run_id)
        assert history
        assert any(event.type == "run.artifact_created" for event in history)
        approval_events = [event for event in history if event.type == "run.approval_waiting"]
        assert approval_events
        assert any(
            event.payload.get("checkpoint_ref") == "task-scheduler-sess"
            or str(event.payload.get("checkpoint_ref", "")).startswith("task-scheduler-sess")
            for event in approval_events
        )

        replay_cutoff = history[2].seq
        expected_slice = [event for event in history if event.seq > replay_cutoff]
        replayed = await event_repo.list(run_id, since_seq=replay_cutoff)
        assert replayed == expected_slice

        expected_frames = [_json_sse_frame(event) for event in expected_slice]
        replay_stream = _build_stream(
            run_id,
            replay_cutoff,
            await event_repo.latest_seq(run_id),
            event_repo,
        )
        actual_frames = await _collect_replay(replay_stream, expected_count=len(expected_frames))
        assert actual_frames == expected_frames
