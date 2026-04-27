"""Run lifecycle service tests.

Proves start/resume/cancel behavior including terminal-state guards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from waywarden.domain.ids import RunEventId, RunId, SessionId, TaskId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.domain.run import Run, RunState
from waywarden.domain.run_event import RunEvent
from waywarden.domain.task import Task
from waywarden.services.run_lifecycle import (
    InvalidResumeKindError,
    RunAlreadyTerminalError,
    RunLifecycleService,
)

# ---------------------------------------------------------------------------
# Minimal in-memory repos for testing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InMemRunRepo:
    _runs: dict[str, Run] = field(default_factory=dict)

    async def create(self, run: Run) -> Run:
        self._runs[str(run.id)] = run
        return run

    async def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    async def load_latest_state(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    async def update_state(
        self,
        run_id: str,
        new_state: str,
        terminal_seq: int | None,
    ) -> Run:
        existing = self._runs.get(run_id)
        if existing is None:
            raise ValueError(f"run {run_id!r} not found")

        updated = Run(
            id=existing.id,
            instance_id=existing.instance_id,
            task_id=existing.task_id,
            profile=existing.profile,
            policy_preset=existing.policy_preset,
            manifest_ref=existing.manifest_ref,
            entrypoint=existing.entrypoint,
            state=cast(RunState, new_state),
            created_at=existing.created_at,
            updated_at=datetime.now(UTC),
            terminal_seq=terminal_seq,
        )
        self._runs[run_id] = updated
        return updated


@dataclass(frozen=True, slots=True)
class InMemEventRepo:
    _events: dict[str, list[RunEvent]] = field(default_factory=dict)
    _latest: dict[str, int] = field(default_factory=dict)

    async def append(self, event: RunEvent) -> RunEvent:
        self._events.setdefault(str(event.run_id), []).append(event)
        self._latest[str(event.run_id)] = event.seq
        return event

    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[RunEvent]:
        result = [e for e in self._events.get(run_id, []) if e.seq > since_seq]
        if limit is not None:
            result = result[:limit]
        return result

    async def latest_seq(self, run_id: str) -> int:
        return self._latest.get(run_id, 0)


@dataclass(frozen=True, slots=True)
class InMemManifestRepo:
    _manifests: dict[str, WorkspaceManifest] = field(default_factory=dict)

    async def save(self, manifest: WorkspaceManifest) -> WorkspaceManifest:
        self._manifests[str(manifest.run_id)] = manifest
        return manifest

    async def get(self, run_id: str) -> WorkspaceManifest | None:
        return self._manifests.get(run_id)


def _make_task() -> Task:
    now = datetime.now(UTC)
    return Task(
        id=TaskId("task-001"),
        session_id=SessionId("session-001"),
        title="Test task",
        objective="Do the thing",
        state="draft",
        created_at=now,
        updated_at=now,
    )


def _make_manifest(run_id: RunId) -> WorkspaceManifest:
    return WorkspaceManifest(
        run_id=run_id,
        inputs=[
            InputMount(
                name="repo",
                kind="directory",
                source_ref="artifact://workspace/repo",
                target_path="/workspace/repo",
                read_only=True,
                required=True,
                description="Test repo",
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
                name="report",
                path="/workspace/output/report.json",
                kind="json",
                required=True,
                promote_to_artifact=True,
            )
        ],
        network_policy=NetworkPolicy(mode="deny", allow=[], deny=[]),
        tool_policy=ToolPolicy(preset="ask", rules=[]),
        secret_scope=SecretScope(
            mode="none",
            allowed_secret_refs=[],
            mount_env=[],
            redaction_level="full",
        ),
        snapshot_policy=SnapshotPolicy(
            on_start=False,
            on_completion=True,
            on_failure=True,
            before_destructive_actions=True,
            max_snapshots=3,
            include_paths=[],
            exclude_paths=[],
        ),
    )


class TestStartEmitsRunCreated:
    @pytest.mark.integration
    async def test_start_emits_run_created(self) -> None:
        manifests = InMemManifestRepo()
        svc = RunLifecycleService(
            runs=InMemRunRepo(),
            events=InMemEventRepo(),
            manifests=manifests,
        )
        task = _make_task()
        run = await svc.start(task, entrypoint="api")
        await manifests.save(_make_manifest(run.id))

        assert run.state == "created"
        events = await svc._events.list(str(run.id))
        assert len(events) == 1
        assert events[0].type == "run.created"
        assert events[0].seq == 1
        assert events[0].payload["entrypoint"] == "api"


class TestResumeRejectsTerminal:
    @pytest.mark.integration
    async def test_resume_rejected_after_terminal(self) -> None:
        runs_repo = InMemRunRepo()
        events_repo = InMemEventRepo()
        svc = RunLifecycleService(
            runs=runs_repo,
            events=events_repo,
            manifests=InMemManifestRepo(),
        )
        task = _make_task()
        run = await svc.start(task)
        # Manually set to terminal state
        await runs_repo.update_state(str(run.id), "completed", terminal_seq=1)

        with pytest.raises(RunAlreadyTerminalError):
            await svc.resume(run.id, resume_kind="operator_resume")


class TestResumeAssignsLatestSeq:
    @pytest.mark.integration
    async def test_resume_assigns_latest_seq(self) -> None:
        runs_repo = InMemRunRepo()
        events_repo = InMemEventRepo()
        svc = RunLifecycleService(
            runs=runs_repo,
            events=events_repo,
            manifests=InMemManifestRepo(),
        )
        task = _make_task()
        run = await svc.start(task)

        # Prepend a non-resume event
        from waywarden.domain.run_event import Actor, Causation

        progress_event = RunEvent(
            id=RunEventId("evt-dummy"),
            run_id=run.id,
            seq=2,
            type="run.progress",
            payload={"phase": "intake", "milestone": "received"},
            timestamp=datetime.now(UTC),
            causation=Causation(event_id=None, action="intake", request_id=None),
            actor=Actor(kind="system", id=None, display=None),
        )
        await events_repo.append(progress_event)

        resumed = await svc.resume(run.id, resume_kind="scheduler_wakeup")

        assert resumed.type == "run.resumed"
        assert resumed.payload["resumed_from_seq"] == 2
        assert resumed.seq == 3


class TestCancelRejectsTerminal:
    @pytest.mark.integration
    async def test_cancel_rejected_after_terminal(self) -> None:
        runs_repo = InMemRunRepo()
        events_repo = InMemEventRepo()
        svc = RunLifecycleService(
            runs=runs_repo,
            events=events_repo,
            manifests=InMemManifestRepo(),
        )
        task = _make_task()
        run = await svc.start(task)

        await runs_repo.update_state(str(run.id), "failed", terminal_seq=5)

        with pytest.raises(RunAlreadyTerminalError):
            await svc.cancel(run.id, reason="something broke")


class TestApprovalGrantResumeKindRejected:
    @pytest.mark.integration
    async def test_approval_granted_resume_kind_rejected(self) -> None:
        runs_repo = InMemRunRepo()
        events_repo = InMemEventRepo()
        svc = RunLifecycleService(
            runs=runs_repo,
            events=events_repo,
            manifests=InMemManifestRepo(),
        )
        task = _make_task()
        run = await svc.start(task)

        with pytest.raises(InvalidResumeKindError):
            await svc.resume(run.id, resume_kind=cast(Any, "approval_granted"))
