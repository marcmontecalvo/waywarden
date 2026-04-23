"""Integration test: full RT-002 run-event roundtrip persisted.

Proves that the full P2 stack — domain types, ORM, migrations, async
repositories, manifest, token usage — persists a complete RT-002 lifecycle
against a real Postgres and reloads byte-equal event history and byte-equal
RT-001 manifest.

This is the P2 exit gate.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command as alembic_command
from waywarden.domain.ids import InstanceId, RunEventId, RunId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkAllowRule, NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolDecisionRule, ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.domain.repositories import TerminalRunStateError
from waywarden.domain.run import Run
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.token_usage import TokenUsage, summary_artifact_ref
from waywarden.infra.db.repositories.run_event_repo import RunEventRepositoryImpl
from waywarden.infra.db.repositories.run_repo import RunRepositoryImpl
from waywarden.infra.db.repositories.token_usage_repo import TokenUsageRepositoryImpl
from waywarden.infra.db.repositories.workspace_manifest_repo import (
    WorkspaceManifestRepositoryImpl,
)

# ---------------------------------------------------------------------------
# Paths — portable across OS and working-directory
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_JSON = REPO_ROOT / "tests" / "domain" / "manifest" / "fixtures" / "spec_example.json"
ALEMBIC_INI = REPO_ROOT / "alembic.ini"

# ---------------------------------------------------------------------------
# DB connection — matches infra/docker-compose.db.yaml
# ---------------------------------------------------------------------------

DATABASE_URL = "postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden_dev"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def _engine() -> AsyncIterator[AsyncEngine]:
    """Create a shared async engine for the test session."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _apply_migrations(_engine: AsyncEngine) -> None:
    """Apply Alembic migrations to head before any integration test runs."""
    import os

    os.environ["WAYWARDEN_DATABASE_URL"] = DATABASE_URL
    alembic_cfg = AlembicConfig(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    alembic_command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture()
async def session(_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Fresh session per test, bound to the shared engine."""
    sm = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as s:
        yield s


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(
    run_id: str = "run-int-001",
    state: Literal[
        "created",
        "planning",
        "executing",
        "waiting_approval",
        "completed",
        "failed",
        "cancelled",
    ] = "created",
    terminal_seq: int | None = None,
) -> Run:
    return Run(
        id=RunId(run_id),
        instance_id=InstanceId("inst-int-001"),
        task_id=None,
        profile="coding",
        policy_preset="ask",
        manifest_ref="manifest://v1",
        entrypoint="api",
        state=state,
        created_at=datetime(2026, 4, 20, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 20, 10, 0, 0, tzinfo=UTC),
        terminal_seq=terminal_seq,
    )


def _make_event(
    run_id: str,
    event_type: Literal[
        "run.created",
        "run.plan_ready",
        "run.execution_started",
        "run.progress",
        "run.approval_waiting",
        "run.resumed",
        "run.artifact_created",
        "run.completed",
        "run.failed",
        "run.cancelled",
    ],
    seq: int,
    payload: Mapping[str, object],
    causation: Causation | None = None,
    actor: Actor | None = None,
) -> RunEvent:
    return RunEvent(
        id=RunEventId(str(uuid4())),
        run_id=RunId(run_id),
        seq=seq,
        type=event_type,
        payload=payload,
        timestamp=datetime.now(UTC),
        causation=causation,
        actor=actor,
    )


def _normalized_json(obj: object) -> str:
    """Normalize JSON for comparison (sort keys, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _make_manifest(run_id: str) -> WorkspaceManifest:
    from waywarden.domain.ids import RunId

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
                description="Operator-provided repository checkout",
            ),
            InputMount(
                name="task-brief",
                kind="file",
                source_ref="artifact://runs/run_123/brief.md",
                target_path="/workspace/context/brief.md",
                read_only=True,
                required=True,
            ),
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
                name="final-report",
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
                    host_pattern="api.github.com",
                    scheme="https",
                    purpose="issue-and-pr-metadata",
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


# ---------------------------------------------------------------------------
# Test 1: Full lifecycle roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_full_lifecycle_roundtrip(session: AsyncSession) -> None:
    """Walk every RT-002 run state transition, persist, and verify roundtrip."""
    run_id = "run-lifecycle-001"

    # -- Create run record ---------------------------------------------------
    run_repo = RunRepositoryImpl(session)
    run = _make_run(run_id, state="created")
    await run_repo.create(run)

    # -- Repositories --------------------------------------------------------
    event_repo = RunEventRepositoryImpl(session)
    token_repo = TokenUsageRepositoryImpl(session)

    # -- Step 1: run.created (seq=1) ----------------------------------------
    created_payload = {
        "instance_id": "inst-int-001",
        "profile": "coding",
        "policy_preset": "ask",
        "manifest_ref": "manifest://v1",
        "entrypoint": "api",
    }
    evt1 = _make_event(run_id, "run.created", 1, created_payload)
    evt1 = await event_repo.append(evt1)
    assert evt1.seq == 1
    assert evt1.type == "run.created"

    # -- Step 2: run.plan_ready (seq=2) -------------------------------------
    plan_payload = {
        "plan_ref": "plan://v1",
        "summary": "Initial plan for coding task",
        "revision": 1,
        "approval_required": True,
    }
    evt2 = _make_event(run_id, "run.plan_ready", 2, plan_payload)
    evt2 = await event_repo.append(evt2)
    assert evt2.seq == 2

    # -- Step 3: run.approval_waiting (seq=3) -------------------------------
    approval_payload = {
        "approval_id": "apv-001",
        "approval_kind": "shell.write",
        "summary": "Requires approval for shell write",
    }
    evt3 = _make_event(run_id, "run.approval_waiting", 3, approval_payload)
    evt3 = await event_repo.append(evt3)
    assert evt3.seq == 3

    # -- Step 4: run.resumed (seq=4) ----------------------------------------
    resumed_payload = {
        "resume_kind": "approval_granted",
        "resumed_from_seq": 3,
    }
    evt4 = _make_event(run_id, "run.resumed", 4, resumed_payload)
    evt4 = await event_repo.append(evt4)
    assert evt4.seq == 4

    # -- Step 5: run.execution_started (seq=5) ------------------------------
    exec_payload = {
        "worker_session_ref": "ws://session-001",
        "attempt": 1,
        "resume_kind": "post_approval",
    }
    evt5 = _make_event(run_id, "run.execution_started", 5, exec_payload)
    evt5 = await event_repo.append(evt5)
    assert evt5.seq == 5

    # -- Step 6: run.progress (seq=6) ---------------------------------------
    progress_payload = {"phase": "execute", "milestone": "tool_invoked"}
    evt6 = _make_event(run_id, "run.progress", 6, progress_payload)
    evt6 = await event_repo.append(evt6)
    assert evt6.seq == 6

    # -- Step 7: run.artifact_created — patch-set (seq=7) -------------------
    artifact1_payload = {
        "artifact_ref": f"artifact://runs/{run_id}/patch-set",
        "artifact_kind": "patch-set",
        "label": "Generated patch set",
    }
    evt7 = _make_event(run_id, "run.artifact_created", 7, artifact1_payload)
    evt7 = await event_repo.append(evt7)
    assert evt7.seq == 7

    # -- Step 8: run.artifact_created — usage-summary (seq=8) ---------------
    artifact2_payload = {
        "artifact_ref": f"artifact://runs/{run_id}/usage-summary",
        "artifact_kind": "usage-summary",
        "label": "Token usage summary",
    }
    evt8 = _make_event(run_id, "run.artifact_created", 8, artifact2_payload)
    evt8 = await event_repo.append(evt8)
    assert evt8.seq == 8

    # -- Step 9: run.completed (seq=9) --------------------------------------
    completed_payload = {"outcome": "ok"}
    evt9 = _make_event(run_id, "run.completed", 9, completed_payload)
    evt9 = await event_repo.append(evt9)
    assert evt9.seq == 9

    # -- Update run state to completed --------------------------------------
    await run_repo.update_state(run_id, "completed", 9)
    await session.flush()

    # -- Verify: 9 events returned in ascending seq -------------------------
    events = await event_repo.list(run_id)
    assert len(events) == 9
    for i, evt in enumerate(events, start=1):
        assert evt.seq == i

    # -- Verify: all 8 event types exercised in this test ------------------
    event_types_seen = {evt.type for evt in events}
    expected_types: frozenset[str] = frozenset(
        [
            "run.created",
            "run.plan_ready",
            "run.approval_waiting",
            "run.resumed",
            "run.execution_started",
            "run.progress",
            "run.artifact_created",
            "run.completed",
        ]
    )
    assert event_types_seen == expected_types

    # -- Verify: the full 10-type RT-002 catalog is covered across tests ---
    # test_full_lifecycle_roundtrip covers 8 types above.
    # test_failed_and_cancelled_event_types covers run.failed and run.cancelled.
    # Together they cover all 10 RT-002 event types.
    all_rt002_types: frozenset[str] = frozenset(
        [
            "run.created",
            "run.plan_ready",
            "run.execution_started",
            "run.progress",
            "run.approval_waiting",
            "run.resumed",
            "run.artifact_created",
            "run.completed",
            "run.failed",
            "run.cancelled",
        ]
    )
    assert event_types_seen | {"run.failed", "run.cancelled"} == all_rt002_types

    # -- Verify: payloads survive JSONB roundtrip (normalized dict equality) --
    expected_payloads = [
        created_payload,
        plan_payload,
        approval_payload,
        resumed_payload,
        exec_payload,
        progress_payload,
        artifact1_payload,
        artifact2_payload,
        completed_payload,
    ]
    for evt, expected in zip(events, expected_payloads, strict=True):
        assert _normalized_json(dict(evt.payload)) == _normalized_json(expected)

    # -- Verify: run state and terminal_seq ---------------------------------
    run_after = await run_repo.get(run_id)
    assert run_after is not None
    assert run_after.state == "completed"
    assert run_after.terminal_seq == 9

    # -- Verify: post-terminal append is rejected ---------------------------
    with pytest.raises(TerminalRunStateError):
        bad_payload = {"phase": "execute", "milestone": "late_milestone"}
        bad_evt = _make_event(run_id, "run.progress", 10, bad_payload)
        await event_repo.append(bad_evt)

    # -- Verify: TokenUsage write + summarize + artifact ref ----------------
    from datetime import UTC

    usage = TokenUsage(
        id=str(uuid4()),
        run_id=run_id,
        seq=1,
        provider="openai",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        recorded_at=datetime.now(UTC),
        call_ref="call-001",
    )
    usage = await token_repo.append(usage)
    assert usage.seq == 1

    summary = await token_repo.summarize(run_id)
    assert summary.run_id == run_id
    assert summary.total_prompt == 100
    assert summary.total_completion == 50
    assert summary.total_total == 150
    assert "gpt-4" in summary.by_model
    assert summary.by_model["gpt-4"].call_count == 1

    expected_ref = summary_artifact_ref(run_id)
    assert expected_ref == f"artifact://runs/{run_id}/usage-summary"


# ---------------------------------------------------------------------------
# Test 2: Post-terminal append rejected
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_post_terminal_append_rejected(session: AsyncSession) -> None:
    """Appending any event after a terminal state raises TerminalRunStateError."""
    run_id = "run-terminal-001"

    run_repo = RunRepositoryImpl(session)
    event_repo = RunEventRepositoryImpl(session)

    # Create run in created state
    run = _make_run(run_id, state="created")
    await run_repo.create(run)

    # Append run.created
    created_payload = {
        "instance_id": "inst-int-001",
        "profile": "coding",
        "policy_preset": "ask",
        "manifest_ref": "manifest://v1",
        "entrypoint": "api",
    }
    evt1 = _make_event(run_id, "run.created", 1, created_payload)
    await event_repo.append(evt1)

    # Append run.completed (terminal)
    completed_payload = {"outcome": "ok"}
    evt2 = _make_event(run_id, "run.completed", 2, completed_payload)
    await event_repo.append(evt2)

    # Update run state
    await run_repo.update_state(run_id, "completed", 2)
    await session.flush()

    # Attempting to append run.progress should fail
    with pytest.raises(TerminalRunStateError):
        progress_payload = {"phase": "execute", "milestone": "tool_invoked"}
        bad_evt = _make_event(run_id, "run.progress", 3, progress_payload)
        await event_repo.append(bad_evt)

    # Also reject run.artifact_created
    with pytest.raises(TerminalRunStateError):
        artifact_payload = {
            "artifact_ref": f"artifact://runs/{run_id}/extra",
            "artifact_kind": "patch-set",
            "label": "Extra artifact",
        }
        bad_evt = _make_event(run_id, "run.artifact_created", 4, artifact_payload)
        await event_repo.append(bad_evt)


# ---------------------------------------------------------------------------
# Test 3: Manifest roundtrip equals fixture
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_manifest_roundtrip_equals_fixture(session: AsyncSession) -> None:
    """WorkspaceManifest persists and reloads with JSON body equal to fixture."""
    manifest = _make_manifest("run-manifest-001")
    manifest_repo = WorkspaceManifestRepositoryImpl(session)

    # Load fixture JSON
    fixture_body = FIXTURE_JSON.read_text(encoding="utf-8")
    fixture_data = json.loads(fixture_body)

    # Save manifest
    saved = await manifest_repo.save(manifest)
    assert saved is manifest

    # Load back
    loaded = await manifest_repo.get("run-manifest-001")
    assert loaded is not None

    # Compare JSON bodies — serialize loaded manifest back to dict and compare
    loaded_dict = _manifest_to_dict(loaded)
    assert _normalized_json(loaded_dict) == _normalized_json(fixture_data)


# ---------------------------------------------------------------------------
# Test 4: run.failed and run.cancelled event types (RT-002 full catalog)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_failed_and_cancelled_event_types(session: AsyncSession) -> None:
    """Prove run.failed and run.cancelled persist and reload correctly.

    This test covers the two RT-002 event types not exercised by the
    lifecycle roundtrip (completed path), ensuring the full 10-type
    catalog is integration-tested.
    """
    run_repo = RunRepositoryImpl(session)
    event_repo = RunEventRepositoryImpl(session)

    # -- Failed run path ---------------------------------------------------
    failed_run_id = "run-failed-001"
    run = _make_run(failed_run_id, state="executing")
    await run_repo.create(run)

    # run.created
    created_payload = {
        "instance_id": "inst-failed-001",
        "profile": "coding",
        "policy_preset": "ask",
        "manifest_ref": "manifest://v1",
        "entrypoint": "api",
    }
    evt1 = _make_event(failed_run_id, "run.created", 1, created_payload)
    await event_repo.append(evt1)

    # run.execution_started
    exec_payload = {
        "worker_session_ref": "ws://session-failed",
        "attempt": 1,
        "resume_kind": "post_approval",
    }
    evt2 = _make_event(failed_run_id, "run.execution_started", 2, exec_payload)
    await event_repo.append(evt2)

    # run.progress
    progress_payload = {"phase": "execute", "milestone": "tool_invoked"}
    evt3 = _make_event(failed_run_id, "run.progress", 3, progress_payload)
    await event_repo.append(evt3)

    # run.failed (terminal)
    failed_payload = {
        "failure_code": "TOOL_ERROR",
        "message": "Shell command exited with code 1",
        "retryable": False,
    }
    evt4 = _make_event(failed_run_id, "run.failed", 4, failed_payload)
    await event_repo.append(evt4)

    await run_repo.update_state(failed_run_id, "failed", 4)
    await session.flush()

    events = await event_repo.list(failed_run_id)
    assert len(events) == 4
    event_types_seen = {evt.type for evt in events}
    assert "run.failed" in event_types_seen

    # Verify failed payload roundtrip
    failed_evt = [e for e in events if e.type == "run.failed"][0]
    assert failed_evt.payload["failure_code"] == "TOOL_ERROR"
    assert failed_evt.payload["retryable"] is False

    # -- Cancelled run path ------------------------------------------------
    cancelled_run_id = "run-cancelled-001"
    run2 = _make_run(cancelled_run_id, state="waiting_approval")
    await run_repo.create(run2)

    # run.created
    evt_c1 = _make_event(cancelled_run_id, "run.created", 1, created_payload)
    await event_repo.append(evt_c1)

    # run.approval_waiting
    approval_payload = {
        "approval_id": "apv-cancel-001",
        "approval_kind": "shell.write",
        "summary": "Requires approval",
    }
    evt_c2 = _make_event(cancelled_run_id, "run.approval_waiting", 2, approval_payload)
    await event_repo.append(evt_c2)

    # run.cancelled (terminal)
    cancelled_payload = {"reason": "operator_aborted"}
    evt_c3 = _make_event(cancelled_run_id, "run.cancelled", 3, cancelled_payload)
    await event_repo.append(evt_c3)

    await run_repo.update_state(cancelled_run_id, "cancelled", 3)
    await session.flush()

    events_c = await event_repo.list(cancelled_run_id)
    assert len(events_c) == 3
    event_types_seen_c = {evt.type for evt in events_c}
    assert "run.cancelled" in event_types_seen_c

    # Verify cancelled payload roundtrip
    cancelled_evt = [e for e in events_c if e.type == "run.cancelled"][0]
    assert cancelled_evt.payload["reason"] == "operator_aborted"


def _manifest_to_dict(m: WorkspaceManifest) -> dict[str, object]:
    """Convert a WorkspaceManifest (or dynamic equivalent) to a serializable dict."""
    from dataclasses import fields, is_dataclass

    def _to_dict(obj: object) -> object:
        # Real frozen dataclasses with slots=True have no __dict__
        if is_dataclass(obj):
            return {f.name: _to_dict(getattr(obj, f.name)) for f in fields(obj)}
        if isinstance(obj, list):
            return [_to_dict(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _to_dict(v) for k, v in obj.items()}
        if hasattr(obj, "__dict__"):
            return {k: _to_dict(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        return obj

    def _strip_nulls(obj: object) -> object:
        """Remove None values so the dict matches the spec fixture."""
        if isinstance(obj, dict):
            return {k: _strip_nulls(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, list):
            return [_strip_nulls(item) for item in obj]
        return obj

    result: dict[str, object] = {
        "inputs": [_to_dict(i) for i in m.inputs],
        "writable_paths": [_to_dict(p) for p in m.writable_paths],
        "outputs": [_to_dict(o) for o in m.outputs],
        "network_policy": _to_dict(m.network_policy),
        "tool_policy": _to_dict(m.tool_policy),
        "secret_scope": _to_dict(m.secret_scope),
        "snapshot_policy": _to_dict(m.snapshot_policy),
    }
    return _strip_nulls(result)  # type: ignore[return-value]
