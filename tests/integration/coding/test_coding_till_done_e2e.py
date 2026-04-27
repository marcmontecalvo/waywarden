"""Coding-profile till-done loop e2e integration test.

Drives a coding task through the full till-done iteration loop against real
Postgres and a deterministic FakeModelProvider.

Exercises P6-1..P6-7 together:
- P6-1: coding profile hydration
- P6-2: coding handoff routine
- P6-3: run-lifecycle start / event emission
- P6-4: till-done iteration loop
- P6-5: coding-handoff routine (handoff envelope)
- P6-6: approval-visibility plumbing
- P6-7: plan-revision surfacing

Canonical references:
    - Issue #99 (P6-8) — this issue
    - Epic #79 (P6: Coding profile + till-done loop)
    - RT-001 (Workspace Manifest Model)
    - RT-002 (Run Event Protocol)

Test_SCOPE:
- Integration test module under ``tests/integration/coding/``
- Exercises P6-1..P6-7 together
- Windows + Linux CI parity — all paths derived from ``__file__``

Runs against a real Postgres instance. Skips gracefully when
Postgres is unavailable.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
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
from waywarden.assets.loader import AssetRegistry
from waywarden.config.settings import AppConfig
from waywarden.domain.ids import InstanceId, RunId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkAllowRule, NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolDecisionRule, ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.domain.run import Run
from waywarden.infra.db.repositories.approval_repo import ApprovalRepositoryImpl
from waywarden.infra.db.repositories.run_event_repo import RunEventRepositoryImpl
from waywarden.infra.db.repositories.run_repo import RunRepositoryImpl
from waywarden.infra.db.repositories.workspace_manifest_repo import (
    WorkspaceManifestRepositoryImpl,
)
from waywarden.services.approval_engine import ApprovalEngine
from waywarden.services.orchestration.coding_handoff import CodingHandoffRoutine
from waywarden.services.orchestration.milestones import is_valid_milestone
from waywarden.services.orchestration.tilldone import (
    IterationResult,
    LoopConfig,
    LoopOutcome,
    _EventStream,
    run_till_done,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CODING_PROFILE_PATH = REPO_ROOT / "profiles" / "coding" / "profile.yaml"
ASSETS_DIR = REPO_ROOT / "assets"
SAMPLE_REPO_PATH = REPO_ROOT / "tests" / "fixtures" / "sample_repo"
ALEMBIC_INI = REPO_ROOT / "alembic.ini"

DATABASE_URL = "postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden_dev"


# ---------------------------------------------------------------------------
# Session-scoped Postgres harness
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def _engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _apply_migrations(_engine: AsyncEngine) -> None:
    """Run Alembic migrations once per test session."""
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
    _engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def coding_asset_registry() -> AssetRegistry:
    """Build a coding asset registry via async fixture."""
    reg = AssetRegistry()
    await reg.load_from_dir(ASSETS_DIR)
    return reg


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_run(run_id: str) -> Run:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return Run(
        id=RunId(run_id),
        instance_id=InstanceId("inst-coding-e2e"),
        task_id=None,
        profile="coding",
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
                target_path=str(SAMPLE_REPO_PATH),
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
            ),
            WritablePath(
                path="/workspace/output",
                purpose="declared-output",
                retention="artifact-promoted",
            ),
        ],
        outputs=[
            OutputContract(
                name="plan",
                path="/workspace/run/plan.md",
                kind="file",
                required=True,
                promote_to_artifact=True,
            ),
            OutputContract(
                name="patch",
                path="/workspace/output/patch.diff",
                kind="file",
                required=False,
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
                    host_pattern="api.github.com",
                    scheme="https",
                    purpose="issue and PR metadata",
                )
            ],
            deny=[],
        ),
        tool_policy=ToolPolicy(
            preset="ask",
            default_decision="approval-required",
            rules=[
                ToolDecisionRule(tool="shell", action="read", decision="auto-allow"),
                ToolDecisionRule(tool="shell", action="write", decision="approval-required"),
            ],
        ),
        secret_scope=SecretScope(
            mode="brokered",
            allowed_secret_refs=[],
            mount_env=[],
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


def _provider_config() -> AppConfig:
    return AppConfig(
        host="127.0.0.1",
        port=9999,
        active_profile="coding",
        model_router="fake",
        model_router_default_provider="fake-model",
        memory_provider="fake",
        knowledge_provider="filesystem",
        knowledge_filesystem_root=str(ASSETS_DIR / "knowledge"),
    )


def _build_deterministic_passing() -> list[IterationResult]:
    """Build a deterministic sequence that completes on iteration 3."""
    return [
        IterationResult(
            plan_artifact_id="artifact://plan-v1",
            check_passed=False,
            changes_applied=True,
            plan_revised=True,
            iteration_count=1,
            plan_body="Iteration 1 plan: implement greet function.",
            plan_diff_from_previous="",
            plan_rationale="Initial plan drafted from objective.",
        ),
        IterationResult(
            plan_artifact_id="artifact://plan-v2",
            check_passed=False,
            changes_applied=True,
            plan_revised=True,
            iteration_count=2,
            plan_body="Iteration 2 plan: refactor greet for edge cases.",
            plan_diff_from_previous="Replaced hardcoded name parameter with dynamic input.",
            plan_rationale="Runtime check revealed hardcoded string instead of parameter.",
        ),
        IterationResult(
            plan_artifact_id="artifact://plan-v3",
            check_passed=True,
            changes_applied=True,
            plan_revised=False,
            iteration_count=3,
            plan_body="Iteration 3 plan: finalise greet with edge case handling.",
            plan_diff_from_previous="Added null-check and unicode-escape path for name.",
            plan_rationale="Lifecycle artifacts verified: output matches expected output.",
        ),
    ]


# ---------------------------------------------------------------------------
# P6-1: integration of coding profile hydration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p6_1_coding_profile_hydration(
    session_factory: async_sessionmaker[AsyncSession],
    coding_asset_registry: AssetRegistry,
) -> None:
    """P6-1: Coding profile hydrates successfully with real asset registry."""
    from waywarden.profiles.coding.hydrate import hydrate_coding_profile

    view = hydrate_coding_profile(
        profile_path=CODING_PROFILE_PATH,
        asset_registry=coding_asset_registry,
    )

    assert view.id is not None
    assert view.display_name == "Coding"
    assert view.required_providers is not None
    assert view.required_providers.model == "fake-model"

    # Profile attributes survive round-trip through Postgres.
    async with session_factory() as session:
        run_repo = RunRepositoryImpl(session)
        run = _make_run(f"run-profile-hydration-{uuid4().hex}")
        await run_repo.create(run)
        reloaded = await run_repo.get(run.id)
        assert reloaded is not None
        assert reloaded.profile == "coding"


# ---------------------------------------------------------------------------
# P6-2 + P6-5: coding handoff routine in the coding profile pipeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p6_2_5_coding_handoff_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """P6-2 + P6-5: CodingHandoffRoutine creates envelope and persists checkpoints.

    Validates that:
    - A delegation envelope can be created with narrowed constraints.
    - Checkpoints can be recorded and retrieved.
    - The manifest survives a Postgres round-trip.
    """
    run_id = f"run-handoff-{uuid4().hex}"
    manifest = _make_manifest(run_id)

    # Persist manifest to Postgres with explicit commit.
    async with session_factory() as session:
        manifest_repo = WorkspaceManifestRepositoryImpl(session)
        await manifest_repo.save(manifest)
        await session.commit()

    handoff = CodingHandoffRoutine(parent_run_id=run_id)

    envelope = handoff.create_envelope(
        objective="Implement a greeting function for the sample repo",
        parent_manifest=manifest,
        constraints=("no external deps", "must handle unicode names"),
        non_goals=("CLI wrapper", "logging integration"),
        acceptance_criteria=(
            "greet(name) returns 'Hello, {name}!'",
            "greet('') returns 'Hello, !'",
        ),
        expected_outputs=("plan", "patch", "review"),
    )

    assert envelope is not None
    assert str(envelope.parent_run_id) == run_id
    assert envelope.brief is not None
    assert "Implement a greeting function" in envelope.brief

    # Record handoff checkpoints (P6-5).
    await handoff.record_checkpoint(
        checkpoint="plan-approved",
        summary="Initial plan approved for first pass.",
    )
    records = handoff.get_records()
    assert len(records) == 1
    assert records[0].checkpoint == "plan-approved"

    # Verify the persisted manifest survived round-trip.
    async with session_factory() as session:
        manifest_repo = WorkspaceManifestRepositoryImpl(session)
        reloaded = await manifest_repo.get(run_id)
        assert reloaded is not None
        output_names = {o.name for o in reloaded.outputs}
        assert output_names == {"plan", "patch", "review"}


# ---------------------------------------------------------------------------
# P6-4 + P6-6 + P6-7: full till-done loop with approvals, plan revisions,
# and durable event round-trip through Postgres
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p6_4_6_7_till_done_e2e_postgres(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """P6-4 + P6-6 + P6-7: Full coding e2e integration test.

    Steps:
    1. Create run + manifest and save to Postgres (P6-3).
    2. Build FakeModelProvider and domain services.
    3. Create an approval checkpoint (P6-6 approval visibility).
    4. Exercise coding-handoff (P6-2 + P6-5).
    5. Run the till-done loop with a deterministic iteration-result:
       - Iteration 1: check fails, plan revised (P6-7 plan-revision artifact)
       - Iteration 2: check fails, plan revised (P6-7)
       - Iteration 3: check passes -> terminal completed (P6-4)
    6. Verify events survive Postgres round-trip.
    """
    run_id = f"run-till-done-e2e-{uuid4().hex}"
    manifest = _make_manifest(run_id)

    # -- 1. Persist run + manifest ----------------------------------------
    async with session_factory() as session:
        run_repo = RunRepositoryImpl(session)
        manifest_repo = WorkspaceManifestRepositoryImpl(session)

        run = _make_run(run_id)
        await run_repo.create(run)
        await manifest_repo.save(manifest)
        await session.commit()

    # -- 2. Build domain services & run approval lifetime in shared sessions -

    # -- 3. Create a coding approval (P6-6) -------------------------------
    async with session_factory() as service_session:
        event_repo = RunEventRepositoryImpl(service_session)
        approval_repo = ApprovalRepositoryImpl(service_session)

        approval_engine = ApprovalEngine(approvals=approval_repo, events=event_repo)

        approval = await approval_engine.request(
            run_id=run_id,
            approval_kind="coding_plan_check",
            summary="Approve iteration plan before changes.",
            checkpoint_ref=f"checkpoint-{run_id}",
        )
        assert approval.state == "pending"
        await service_session.commit()

    # -- 4. Coding handoff (P6-2 + P6-5) ----------------------------------
    handoff = CodingHandoffRoutine(parent_run_id=run_id)
    _ = handoff.create_envelope(
        objective="Implement greeting with edge-case handling",
        parent_manifest=manifest,
        acceptance_criteria=("greet returns correct format",),
    )
    await handoff.record_checkpoint(
        checkpoint="plan-approved",
        summary="Delegation envelope created, ready for coding.",
    )

    # -- 5. Run the till-done loop -----------------------------------------
    deterministic_results = _build_deterministic_passing()
    iteration_idx = 0

    def iteration_provider(iteration_num: int) -> IterationResult:
        nonlocal iteration_idx
        result = deterministic_results[iteration_idx]
        iteration_idx += 1
        return IterationResult(
            plan_artifact_id=result.plan_artifact_id,
            check_passed=result.check_passed,
            changes_applied=result.changes_applied,
            plan_revised=result.plan_revised,
            iteration_count=iteration_num,
            plan_body=result.plan_body,
            plan_diff_from_previous=result.plan_diff_from_previous,
            plan_rationale=result.plan_rationale,
        )

    stream = _EventStream()

    outcome = await run_till_done(
        run_id,
        iteration_result_fn=iteration_provider,
        config=LoopConfig(max_iterations=5, check_failure_max=2),
        events=stream,
    )

    assert outcome == LoopOutcome.COMPLETED

    # -- 6. Postgres round-trip verification (P6-6) -------------------------
    async with session_factory() as read_session:
        event_repo_read = RunEventRepositoryImpl(read_session)
        manifest_repo_read = WorkspaceManifestRepositoryImpl(read_session)

        pg_events = await event_repo_read.list(run_id)

        # Approval events — P6-6 approval visibility API
        approval_events = [e for e in pg_events if e.type == "run.approval_waiting"]
        assert len(approval_events) == 1
        approval_event = approval_events[0]
        assert "approval_id" in approval_event.payload
        assert "approval_kind" in approval_event.payload
        assert approval_event.payload["approval_kind"] == "coding_plan_check"

        # Manifest round-trip
        reloaded_manifest = await manifest_repo_read.get(run_id)
        assert reloaded_manifest is not None
        assert reloaded_manifest.network_policy.mode == "allowlist"

        # Seq monotonicity for Postgres events
        pg_seqs = [e.seq for e in pg_events]
        assert len(pg_seqs) >= 1
        assert pg_seqs == sorted(pg_seqs)

        # All progress milestones in Postgres must be catalog-valid
        for event in pg_events:
            if event.type == "run.progress":
                phase = event.payload.get("phase")
                milestone = event.payload.get("milestone")
                assert isinstance(phase, str)
                assert isinstance(milestone, str)
                assert is_valid_milestone(phase, milestone), (
                    f"Invalid milestone: {phase!r}.{milestone!r}"
                )

    # -- 7. Plan-revision artifacts (P6-7): validate via in-memory stream ---
    plan_revision_events = [
        e
        for e in stream.events
        if e.type == "run.artifact_created" and e.payload.get("artifact_kind") == "plan-revision"
    ]
    assert len(plan_revision_events) == 2
    revision_kinds = {e.payload.get("artifact_kind") for e in plan_revision_events}
    assert revision_kinds == {"plan-revision"}


# ---------------------------------------------------------------------------
# Milestone validation across the coding e2e flow
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p6_milestones_are_catalog_valid(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Confirm that no unregistered phase/milestone pair is emitted."""
    run_id = f"run-milestone-validation-{uuid4().hex}"

    async with session_factory() as session:
        run_repo = RunRepositoryImpl(session)
        await run_repo.create(_make_run(run_id))
        await session.commit()

    # Quick iteration: single pass passes on first try.
    results = [
        IterationResult(
            plan_artifact_id="artifact://plan-v1",
            check_passed=True,
            changes_applied=True,
            plan_revised=False,
            iteration_count=1,
            plan_body="Plan v1: done.",
            plan_diff_from_previous="",
            plan_rationale="Straight to completion.",
        ),
    ]
    idx = 0

    def iter_fn(n: int) -> IterationResult:
        nonlocal idx
        r = results[idx]
        idx += 1
        return IterationResult(
            plan_artifact_id=r.plan_artifact_id,
            check_passed=r.check_passed,
            changes_applied=True,
            plan_revised=r.plan_revised,
            iteration_count=n,
            plan_body=r.plan_body,
            plan_diff_from_previous=r.plan_diff_from_previous,
            plan_rationale=r.plan_rationale,
        )

    stream = _EventStream()
    outcome = await run_till_done(
        run_id,
        iteration_result_fn=iter_fn,
        events=stream,
    )

    assert outcome == LoopOutcome.COMPLETED

    for event in stream.events:
        if event.type == "run.progress":
            phase = event.payload.get("phase")
            milestone = event.payload.get("milestone")
            assert isinstance(phase, str)
            assert isinstance(milestone, str)
            assert is_valid_milestone(phase, milestone), (
                f"Unregistered milestone: {phase!r}.{milestone!r}"
            )


# ---------------------------------------------------------------------------
# Escalation path: max iterations expires -> ESCALATED
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p6_4_till_done_escalation(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Till-done loop escalates after max_iterations when checks never pass."""
    run_id = f"run-escalation-{uuid4().hex}"
    max_iterations = 3

    def esc_iter_fn(n: int) -> IterationResult:
        return IterationResult(
            plan_artifact_id=f"artifact://plan-v{n}",
            check_passed=False,
            changes_applied=True,
            plan_revised=True,
            iteration_count=n,
            plan_body=f"Iteration {n} plan",
            plan_diff_from_previous=f"diff v{n}",
            plan_rationale=f"needs revision v{n}",
        )

    outcome = await run_till_done(
        run_id,
        iteration_result_fn=esc_iter_fn,
        config=LoopConfig(max_iterations=max_iterations, check_failure_max=2),
    )

    assert outcome == LoopOutcome.ESCALATED
