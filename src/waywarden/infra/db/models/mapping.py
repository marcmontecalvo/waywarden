"""Imperative ORM mappings — maps domain types to tables.

Each ``map_<aggregate>`` function registers the mapping for one aggregate.
Importing this module side-effects the SQLAlchemy registry so that
``metadata.tables`` contains every table and the mapper registry knows
about every domain type.
"""

from __future__ import annotations

from sqlalchemy.orm import registry

from waywarden.domain.approval import Approval
from waywarden.domain.checkpoint import Checkpoint
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.message import Message
from waywarden.domain.run import Run
from waywarden.domain.run_event import RunEvent
from waywarden.domain.session import Session
from waywarden.domain.task import Task

from . import approval as approval_table
from . import checkpoint as checkpoint_table
from . import message as message_table
from . import run as run_table
from . import run_event as run_event_table
from . import session as session_table
from . import task as task_table
from . import token_usage as token_usage_table
from . import workspace_manifest as ws_manifest_table

_mapper = registry()


def map_session() -> None:
    _mapper.map_imperatively(Session, session_table.sessions)


def map_message() -> None:
    _mapper.map_imperatively(Message, message_table.messages)


def map_task() -> None:
    _mapper.map_imperatively(Task, task_table.tasks)


def map_approval() -> None:
    _mapper.map_imperatively(Approval, approval_table.approvals)


def map_run() -> None:
    _mapper.map_imperatively(Run, run_table.runs)


def map_run_event() -> None:
    _mapper.map_imperatively(RunEvent, run_event_table.run_events)


def map_workspace_manifest() -> None:
    _mapper.map_imperatively(WorkspaceManifest, ws_manifest_table.workspace_manifests)


def map_checkpoint() -> None:
    _mapper.map_imperatively(Checkpoint, checkpoint_table.checkpoints)


def map_token_usage() -> None:
    _mapper.map_imperatively(type("TokenUsage", (), {}), token_usage_table.token_usage)


def map_all() -> None:
    """Register all domain-to-table mappings.

    Call once at application startup or before generating migrations.
    """
    map_session()
    map_message()
    map_task()
    map_approval()
    map_run()
    map_run_event()
    map_workspace_manifest()
    map_checkpoint()
    map_token_usage()
