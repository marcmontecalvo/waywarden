"""Tests for the coding-handoff routine (P6-5 #96)."""

from __future__ import annotations

import json
from typing import Any

import anyio
import pytest

from waywarden.assets.loader import AssetRegistry
from waywarden.assets.schema import RoutineMetadata
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.domain.run_event import RunEvent
from waywarden.services.orchestration.milestones import is_valid_milestone


class _InMemoryEventRepo:
    def __init__(self) -> None:
        self.events: list[RunEvent] = []
        self._seqs: dict[str, int] = {}

    async def append(self, event: RunEvent) -> RunEvent:
        run_id = str(event.run_id)
        seq = self._seqs.get(run_id, 0) + 1
        confirmed = RunEvent(
            id=RunEventId(str(event.id)),
            run_id=RunId(run_id),
            seq=seq,
            type=event.type,
            payload=event.payload,
            timestamp=event.timestamp,
            causation=event.causation,
            actor=event.actor,
        )
        self._seqs[run_id] = seq
        self.events.append(confirmed)
        return confirmed

    async def list(
        self, run_id: str, *, since_seq: int = 0, limit: int | None = None
    ) -> list[RunEvent]:
        matches = [event for event in self.events if str(event.run_id) == run_id]
        filtered = [event for event in matches if event.seq > since_seq]
        if limit is not None:
            return filtered[:limit]
        return filtered

    async def latest_seq(self, run_id: str) -> int:
        return self._seqs.get(run_id, 0)


def _parent_manifest() -> WorkspaceManifest:
    return WorkspaceManifest(
        run_id=RunId("run-parent"),
        inputs=[
            InputMount(
                name="repo",
                kind="directory",
                source_ref="artifact://workspace/repo",
                target_path="/workspace/repo",
                read_only=True,
            )
        ],
        writable_paths=[
            WritablePath(
                path="/workspace/output",
                purpose="declared-output",
                retention="artifact-promoted",
            )
        ],
        outputs=[
            OutputContract(
                name="plan",
                path="/workspace/output/plan.md",
                kind="file",
                required=True,
            ),
            OutputContract(
                name="patch",
                path="/workspace/output/changes.patch",
                kind="patch-set",
                required=True,
            ),
            OutputContract(
                name="review",
                path="/workspace/output/review.md",
                kind="report",
                required=False,
            ),
        ],
        network_policy=NetworkPolicy(mode="deny", allow=[], deny=[]),
        tool_policy=ToolPolicy(preset="ask", rules=[], default_decision="approval-required"),
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


@pytest.mark.anyio
async def test_coding_handoff_asset_loads_with_checkpoint_contract() -> None:
    registry = AssetRegistry()
    await registry.load_from_dir("assets/routines/coding-handoff")
    asset = registry.get("coding-handoff", kind="routine")

    assert isinstance(asset, RoutineMetadata)
    assert asset.id == "coding-handoff"
    assert "coding" in asset.tags
    assert asset.required_providers == ("model", "tool")
    assert asset.emits_events == ("run.progress",)
    assert asset.milestones == (
        {
            "phase": "handoff",
            "names": ["envelope_emitted"],
            "checkpoints": [
                "plan-approved",
                "implementation-complete",
                "review-found-issues",
            ],
        },
    )


@pytest.mark.anyio
async def test_coding_handoff_attaches_narrowed_rt001_manifest() -> None:
    from waywarden.services.orchestration.coding_handoff import CodingHandoffRoutine

    routine = CodingHandoffRoutine(parent_run_id="run-parent")
    parent_manifest = _parent_manifest()
    envelope = routine.create_envelope(
        objective="Implement a bounded code change",
        parent_manifest=parent_manifest,
        constraints=("stay within issue scope",),
        acceptance_criteria=("tests prove the change",),
        artifact_context={"plan_ref": "artifact://runs/run-parent/plan-v1"},
    )

    assert envelope.brief.startswith("Coding handoff: Implement a bounded code change")
    assert envelope.child_manifest is not parent_manifest
    assert envelope.child_manifest.writable_paths == parent_manifest.writable_paths
    assert envelope.child_manifest.network_policy == parent_manifest.network_policy
    assert envelope.child_manifest.tool_policy == parent_manifest.tool_policy
    assert envelope.child_manifest.secret_scope == parent_manifest.secret_scope
    assert tuple(envelope.expected_outputs) == ("plan", "patch", "review")


@pytest.mark.anyio
async def test_coding_handoff_rejects_outputs_missing_from_child_manifest() -> None:
    from waywarden.services.orchestration.coding_handoff import CodingHandoffRoutine

    routine = CodingHandoffRoutine(parent_run_id="run-parent")

    with pytest.raises(ValueError, match="expected_outputs"):
        routine.create_envelope(
            objective="Implement a bounded code change",
            parent_manifest=_parent_manifest(),
            expected_outputs=("not-declared",),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("checkpoint", "summary"),
    [
        ("plan-approved", "Operator approved the coding plan"),
        ("implementation-complete", "Patch and checks are complete"),
        ("review-found-issues", "Review found blocking defects"),
    ],
)
async def test_coding_handoff_emits_visible_checkpoint_events(
    checkpoint: str,
    summary: str,
) -> None:
    from waywarden.services.orchestration.coding_handoff import CodingHandoffRoutine

    events = _InMemoryEventRepo()
    routine = CodingHandoffRoutine(parent_run_id="run-parent", events=events)
    envelope = routine.create_envelope(
        objective="Implement a bounded code change",
        parent_manifest=_parent_manifest(),
    )

    record = await routine.record_checkpoint(checkpoint, summary)

    assert record.checkpoint == checkpoint
    assert len(events.events) == 1
    event = events.events[0]
    assert event.type == "run.progress"
    assert event.payload["phase"] == "handoff"
    assert event.payload["milestone"] == "envelope_emitted"
    assert is_valid_milestone(str(event.payload["phase"]), str(event.payload["milestone"]))
    assert event.payload["detail"] == {
        "checkpoint": checkpoint,
        "summary": summary,
        "routine": "coding-handoff",
        "delegation_id": str(envelope.id),
    }


@pytest.mark.anyio
async def test_coding_handoff_checkpoint_events_are_visible_via_sse() -> None:
    from waywarden.api.routers.run_events import _build_stream
    from waywarden.services.orchestration.coding_handoff import CodingHandoffRoutine

    events = _InMemoryEventRepo()
    routine = CodingHandoffRoutine(parent_run_id="run-parent", events=events)
    routine.create_envelope(
        objective="Implement a bounded code change",
        parent_manifest=_parent_manifest(),
    )

    await routine.record_checkpoint("plan-approved", "Operator approved the coding plan")
    await routine.record_checkpoint("implementation-complete", "Patch and checks are complete")
    await routine.record_checkpoint("review-found-issues", "Review found blocking defects")

    frames: list[dict[str, Any]] = []
    with anyio.fail_after(1):
        async for frame in _build_stream("run-parent", 0, 3, events):
            text = frame.decode("utf-8")
            for line in text.splitlines():
                if line.startswith("data: "):
                    frames.append(json.loads(line[len("data: ") :]))
            if len(frames) == 3:
                break

    assert [frame["payload"]["detail"]["checkpoint"] for frame in frames] == [
        "plan-approved",
        "implementation-complete",
        "review-found-issues",
    ]
    assert all(frame["type"] == "run.progress" for frame in frames)
    assert all(frame["payload"]["phase"] == "handoff" for frame in frames)
    assert all(frame["payload"]["milestone"] == "envelope_emitted" for frame in frames)
