"""Tests for the RT-002 Run domain model."""

from datetime import UTC, datetime

import pytest

from waywarden.domain.ids import InstanceId, RunId, TaskId
from waywarden.domain.run import Run


def test_run_state_literal_enforced() -> None:
    with pytest.raises(ValueError, match="state must be one of"):
        Run(
            id=RunId("run-1"),
            instance_id=InstanceId("inst-1"),
            task_id=None,
            profile="default",
            policy_preset="yolo",
            manifest_ref="manifest://v1",
            entrypoint="api",
            state="running",  # type: ignore[arg-type]
            created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
            terminal_seq=None,
        )


def test_policy_preset_enforced() -> None:
    with pytest.raises(ValueError, match="policy_preset must be one of"):
        Run(
            id=RunId("run-1"),
            instance_id=InstanceId("inst-1"),
            task_id=None,
            profile="default",
            policy_preset="unsafe",  # type: ignore[arg-type]
            manifest_ref="manifest://v1",
            entrypoint="api",
            state="created",
            created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
            terminal_seq=None,
        )


def test_entrypoint_enforced() -> None:
    with pytest.raises(ValueError, match="entrypoint must be one of"):
        Run(
            id=RunId("run-1"),
            instance_id=InstanceId("inst-1"),
            task_id=None,
            profile="default",
            policy_preset="yolo",
            manifest_ref="manifest://v1",
            entrypoint="web",  # type: ignore[arg-type]
            state="created",
            created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
            terminal_seq=None,
        )


def test_terminal_seq_must_be_positive() -> None:
    with pytest.raises(ValueError, match="terminal_seq must be >= 1"):
        Run(
            id=RunId("run-1"),
            instance_id=InstanceId("inst-1"),
            task_id=None,
            profile="default",
            policy_preset="yolo",
            manifest_ref="manifest://v1",
            entrypoint="api",
            state="completed",
            created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
            terminal_seq=0,
        )


def test_updated_at_not_before_created_at() -> None:
    with pytest.raises(ValueError, match="updated_at must not be before"):
        Run(
            id=RunId("run-1"),
            instance_id=InstanceId("inst-1"),
            task_id=None,
            profile="default",
            policy_preset="yolo",
            manifest_ref="manifest://v1",
            entrypoint="api",
            state="created",
            created_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
            updated_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            terminal_seq=None,
        )


def test_non_utc_timestamp_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Run(
            id=RunId("run-1"),
            instance_id=InstanceId("inst-1"),
            task_id=None,
            profile="default",
            policy_preset="yolo",
            manifest_ref="manifest://v1",
            entrypoint="api",
            state="created",
            created_at=datetime(2026, 4, 19, 14, 0),
            updated_at=datetime(2026, 4, 19, 14, 1),
            terminal_seq=None,
        )


def test_valid_run() -> None:
    run = Run(
        id=RunId("run-1"),
        instance_id=InstanceId("inst-1"),
        task_id=TaskId("task-1"),
        profile="default",
        policy_preset="ask",
        manifest_ref="manifest://v1",
        entrypoint="cli",
        state="created",
        created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
        terminal_seq=None,
    )
    assert run.id == RunId("run-1")
    assert run.terminal_seq is None
    assert run.state == "created"
