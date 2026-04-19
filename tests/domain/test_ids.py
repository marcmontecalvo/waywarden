from typing import assert_type

from waywarden.domain.ids import ApprovalId, InstanceId, MessageId, RunId, SessionId, TaskId


def _needs_session_id(value: SessionId) -> SessionId:
    return value


def _needs_message_id(value: MessageId) -> MessageId:
    return value


def _needs_instance_id(value: InstanceId) -> InstanceId:
    return value


def _needs_task_id(value: TaskId) -> TaskId:
    return value


def _needs_approval_id(value: ApprovalId) -> ApprovalId:
    return value


def _needs_run_id(value: RunId) -> RunId:
    return value


def test_newtypes_distinguish_at_type_level() -> None:
    session_id = SessionId("session-1")
    message_id = MessageId("message-1")
    instance_id = InstanceId("coding-main")
    task_id = TaskId("task-1")
    approval_id = ApprovalId("approval-1")
    run_id = RunId("run-1")

    assert_type(_needs_session_id(session_id), SessionId)
    assert_type(_needs_message_id(message_id), MessageId)
    assert_type(_needs_instance_id(instance_id), InstanceId)
    assert_type(_needs_task_id(task_id), TaskId)
    assert_type(_needs_approval_id(approval_id), ApprovalId)
    assert_type(_needs_run_id(run_id), RunId)
