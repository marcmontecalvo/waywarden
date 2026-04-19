from datetime import UTC, datetime

import pytest

from waywarden.domain.ids import SessionId, TaskId
from waywarden.domain.task import Task


def test_task_state_literal_enforced() -> None:
    with pytest.raises(ValueError, match="state must be one of"):
        Task(
            id=TaskId("task-1"),
            session_id=SessionId("session-1"),
            title="Ship persistence domain",
            objective="Model task records for RT-002-aligned execution",
            state="queued",  # type: ignore[arg-type]
            created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
        )


def test_updated_at_not_before_created_at() -> None:
    with pytest.raises(ValueError, match="updated_at must not be before created_at"):
        Task(
            id=TaskId("task-1"),
            session_id=SessionId("session-1"),
            title="Ship persistence domain",
            objective="Model task records for RT-002-aligned execution",
            state="draft",
            created_at=datetime(2026, 4, 19, 14, 1, tzinfo=UTC),
            updated_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
        )
