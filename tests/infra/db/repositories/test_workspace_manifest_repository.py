"""Integration tests for WorkspaceManifestRepository."""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.domain.ids import RunId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkAllowRule, NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolDecisionRule, ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.infra.db.repositories.workspace_manifest_repo import (
    WorkspaceManifestRepositoryImpl,
)


def _make_manifest(run_id: str = "run_001") -> WorkspaceManifest:
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
                description="Test repo",
            ),
        ],
        writable_paths=[
            WritablePath(
                path="/workspace/run",
                purpose="task-scratch",
                retention="ephemeral",
            ),
        ],
        outputs=[
            OutputContract(
                name="report",
                path="/workspace/output/report.json",
                kind="json",
                required=True,
                promote_to_artifact=True,
            ),
        ],
        network_policy=NetworkPolicy(
            mode="allowlist",
            allow=[
                NetworkAllowRule(
                    host_pattern="api.example.com",
                    scheme="https",
                    purpose="test",
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
            include_paths=["/workspace/output"],
            exclude_paths=["/workspace/run/tmp"],
        ),
    )


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE workspace_manifests (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    body TEXT NOT NULL
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_save_twice_no_crash(session: AsyncSession) -> None:
    """Saving twice for same run_id does not crash."""
    manifest = _make_manifest("run_twice")
    repo = WorkspaceManifestRepositoryImpl(session)

    await repo.save(manifest)
    # Second save must not raise UniqueViolation
    await repo.save(manifest)


async def test_save_roundtrip(session: AsyncSession) -> None:
    """Save and reload returns a manifest with matching fields."""
    manifest = _make_manifest("run_rt")
    repo = WorkspaceManifestRepositoryImpl(session)

    await repo.save(manifest)
    loaded = await repo.get("run_rt")
    assert loaded is not None

    # The loaded manifest should have the same run_id and structure
    assert loaded.run_id == manifest.run_id
    assert len(loaded.inputs) == 1
    assert loaded.inputs[0].name == "repo"
    assert len(loaded.writable_paths) == 1
    assert loaded.writable_paths[0].path == "/workspace/run"
    assert len(loaded.outputs) == 1
    assert loaded.outputs[0].name == "report"


async def test_get_nonexistent_returns_none(session: AsyncSession) -> None:
    """get() returns None for a run_id that was never saved."""
    repo = WorkspaceManifestRepositoryImpl(session)
    loaded = await repo.get("nonexistent")
    assert loaded is None


async def test_nested_dataclass_fields_survive_roundtrip(session: AsyncSession) -> None:
    """Nested dataclass fields (network_policy, tool_policy, etc.) survive save+get."""
    manifest = _make_manifest("run_nested")
    repo = WorkspaceManifestRepositoryImpl(session)

    await repo.save(manifest)
    loaded = await repo.get("run_nested")
    assert loaded is not None

    # Verify nested dataclass fields are proper dataclass instances, not type() objects
    assert isinstance(loaded.network_policy, NetworkPolicy)
    assert loaded.network_policy.mode == "allowlist"
    assert len(loaded.network_policy.allow) == 1
    assert loaded.network_policy.allow[0].host_pattern == "api.example.com"

    assert isinstance(loaded.tool_policy, ToolPolicy)
    assert loaded.tool_policy.preset == "ask"
    assert loaded.tool_policy.default_decision == "approval-required"
    assert len(loaded.tool_policy.rules) == 1
    assert loaded.tool_policy.rules[0].tool == "shell"

    assert isinstance(loaded.secret_scope, SecretScope)
    assert loaded.secret_scope.mode == "brokered"
    assert loaded.secret_scope.redaction_level == "full"

    assert isinstance(loaded.snapshot_policy, SnapshotPolicy)
    assert loaded.snapshot_policy.on_start is False
    assert loaded.snapshot_policy.on_completion is True
    assert loaded.snapshot_policy.max_snapshots == 3
    assert "/workspace/output" in loaded.snapshot_policy.include_paths
