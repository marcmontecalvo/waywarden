from typing import assert_type

from waywarden.domain.ids import InstanceId, MessageId, SessionId


def _needs_session_id(value: SessionId) -> SessionId:
    return value


def _needs_message_id(value: MessageId) -> MessageId:
    return value


def _needs_instance_id(value: InstanceId) -> InstanceId:
    return value


def test_newtypes_distinguish_at_type_level() -> None:
    session_id = SessionId("session-1")
    message_id = MessageId("message-1")
    instance_id = InstanceId("coding-main")

    assert_type(_needs_session_id(session_id), SessionId)
    assert_type(_needs_message_id(message_id), MessageId)
    assert_type(_needs_instance_id(instance_id), InstanceId)
