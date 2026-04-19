from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from waywarden.domain.ids import InstanceId, SessionId
from waywarden.domain.session import Session


def test_session_is_frozen() -> None:
    session = Session(
        id=SessionId("session-1"),
        instance_id=InstanceId("coding-main"),
        profile="coding",
        created_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
    )

    with pytest.raises(FrozenInstanceError):
        session.profile = "ea"  # type: ignore[misc]


def test_session_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="created_at"):
        Session(
            id=SessionId("session-1"),
            instance_id=InstanceId("coding-main"),
            profile="coding",
            created_at=datetime(2026, 4, 19, 14, 0),
        )
