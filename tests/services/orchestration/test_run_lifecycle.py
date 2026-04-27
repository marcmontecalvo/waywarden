"""Integration tests for the orchestration service.

Uses fake repositories backed by in-memory structures to prove the
full run lifecycle and milestone catalog compliance against Postgres-like
persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from waywarden.domain.ids import RunId, TaskId
from waywarden.domain.run import Run, RunState
from waywarden.domain.run_event import RunEvent
from waywarden.services.orchestration.milestones import MILESTONE_CATALOG
from waywarden.services.orchestration.service import OrchestrationService

# ---------------------------------------------------------------------------
# Minimal fake repositories for integration testing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FakeRunRepository:
    """In-memory Run repository."""

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
class FakeRunEventRepository:
    """Append-only in-memory RunEvent repository."""

    _events: dict[str, list[RunEvent]] = field(default_factory=dict)
    _seq_counters: dict[str, int] = field(default_factory=dict)

    async def append(self, event: RunEvent) -> RunEvent:
        run_events = self._events.setdefault(str(event.run_id), [])
        run_events.append(event)
        self._seq_counters[str(event.run_id)] = event.seq
        return event

    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[RunEvent]:
        events = self._events.get(run_id, [])
        result = [e for e in events if e.seq > since_seq]
        if limit is not None:
            result = result[:limit]
        return result

    async def latest_seq(self, run_id: str) -> int:
        return self._seq_counters.get(run_id, 0)


@dataclass(frozen=True, slots=True)
class FakeApprovalEngine:
    """Stub approval engine for orchestration integration tests."""

    async def request(
        self,
        run_id: str,
        approval_kind: str,
        summary: str,
        **_: Any,
    ) -> Any:
        return None

    async def resolve(self, approval_id: str, decision: Any) -> Any:
        return None


def _make_run() -> Run:
    from waywarden.domain.ids import InstanceId

    now = datetime.now(UTC)
    return Run(
        id=RunId("run-001"),
        instance_id=InstanceId("inst-001"),
        task_id=TaskId("task-001"),
        profile="ea",
        policy_preset="ask",
        manifest_ref="manifest://v1",
        entrypoint="api",
        state="created",
        created_at=now,
        updated_at=now,
        terminal_seq=None,
    )


class TestFullHappyPathEmitsCanonicalSequence:
    """Integration tests proving the full orchestration sequence."""

    @pytest.mark.integration
    async def test_full_happy_path_emits_canonical_sequence(self) -> None:
        """The full happy path emits all milestone progress events plus the
        terminal usage-summary artifact, all in ascending seq order."""
        runs_repo = FakeRunRepository()
        events_repo = FakeRunEventRepository()
        approvals = FakeApprovalEngine()

        service = OrchestrationService(
            runs=runs_repo,
            events=events_repo,
            approvals=cast(Any, approvals),
        )

        run = await runs_repo.create(_make_run())
        final_run = await service.run(run)

        assert final_run.state == "completed"

        # Verify all events are in ascending seq order.
        all_events = await events_repo.list("run-001")
        seqs = [e.seq for e in all_events]
        assert seqs == sorted(seqs), "Events must be in ascending seq order"
        assert seqs == list(range(1, len(seqs) + 1)), "No gaps in seq"

        # Verify milestones were emitted for each phase
        phases_seen: set[str] = set()
        for event in all_events:
            if event.type == "run.progress":
                phases_seen.add(cast(str, event.payload["phase"]))

        assert phases_seen == {"intake", "plan", "execute", "review", "handoff"}

    @pytest.mark.integration
    async def test_progress_events_use_catalog_values(self) -> None:
        """Every run.progress emitted uses phase/milestone pairs from the
        milestone catalog."""
        runs_repo = FakeRunRepository()
        events_repo = FakeRunEventRepository()
        approvals = FakeApprovalEngine()

        service = OrchestrationService(
            runs=runs_repo,
            events=events_repo,
            approvals=cast(Any, approvals),
        )

        run = await runs_repo.create(_make_run())
        await service.run(run)

        all_events = await events_repo.list("run-001")
        for event in all_events:
            if event.type == "run.progress":
                phase = event.payload["phase"]
                milestone = event.payload["milestone"]
                valid = any(
                    md.phase == phase and md.milestone == milestone for md in MILESTONE_CATALOG
                )
                assert valid, (
                    f"progress event phase={phase!r}, milestone={milestone!r} "
                    f"is not in the milestone catalog"
                )

    @pytest.mark.integration
    async def test_terminal_usage_summary_artifact_emitted(self) -> None:
        """Before run.completed, a usage-summary artifact is registered."""
        runs_repo = FakeRunRepository()
        events_repo = FakeRunEventRepository()
        approvals = FakeApprovalEngine()

        service = OrchestrationService(
            runs=runs_repo,
            events=events_repo,
            approvals=cast(Any, approvals),
        )

        run = await runs_repo.create(_make_run())
        await service.run(run)

        all_events = await events_repo.list("run-001")
        usage_artifact_seq: int | None = None
        completed_seq: int | None = None
        for event in all_events:
            if (
                event.type == "run.artifact_created"
                and event.payload.get("artifact_kind") == "usage-summary"
            ):
                usage_artifact_seq = event.seq
            if event.type == "run.completed":
                completed_seq = event.seq

        assert usage_artifact_seq is not None, (
            "usage-summary artifact must be emitted before run.completed"
        )
        assert completed_seq is not None, "run.completed must be emitted"
        assert usage_artifact_seq < completed_seq, (
            "usage-summary artifact must be emitted before run.completed"
        )
