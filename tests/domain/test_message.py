from datetime import UTC, datetime
from typing import Any, cast

import pytest

from waywarden.domain.ids import MessageId, SessionId
from waywarden.domain.message import Message


def test_invalid_role_rejected() -> None:
    with pytest.raises(ValueError, match="role must be one of"):
        Message(
            id=MessageId("message-1"),
            session_id=SessionId("session-1"),
            role="moderator",  # type: ignore[arg-type]
            content="Hello",
            created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            metadata={"channel": "cli"},
        )


def test_metadata_is_immutable() -> None:
    message = Message(
        id=MessageId("message-1"),
        session_id=SessionId("session-1"),
        role="assistant",
        content="Hello",
        created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
        metadata={"channel": "cli"},
    )

    with pytest.raises(TypeError):
        cast(Any, message.metadata)["channel"] = "api"


def test_metadata_must_be_mapping() -> None:
    with pytest.raises(TypeError, match="metadata must be a mapping"):
        Message(
            id=MessageId("message-1"),
            session_id=SessionId("session-1"),
            role="assistant",
            content="Hello",
            created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            metadata=cast(Any, ["channel", "cli"]),
        )


def test_message_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="created_at"):
        Message(
            id=MessageId("message-1"),
            session_id=SessionId("session-1"),
            role="assistant",
            content="Hello",
            created_at=datetime(2026, 4, 19, 14, 0),
            metadata={},
        )
