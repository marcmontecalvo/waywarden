"""Repository Protocols for all domain aggregates."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from waywarden.domain.approval import Approval
from waywarden.domain.checkpoint import Checkpoint
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.message import Message
from waywarden.domain.run import Run
from waywarden.domain.run_event import RunEvent
from waywarden.domain.session import Session
from waywarden.domain.task import Task


class TerminalRunStateError(Exception):
    """Raised when attempting to append to a terminal-run run."""


@runtime_checkable
class SessionRepository(Protocol):
    """Persist provider-neutral session records."""

    async def get(self, id: str) -> Session | None: ...
    async def save(self, session: Session) -> Session: ...


@runtime_checkable
class MessageRepository(Protocol):
    """Persist provider-neutral message records."""

    async def get(self, id: str) -> Message | None: ...
    async def save(self, message: Message) -> Message: ...
    async def list_by_session(
        self,
        session_id: str,
        *,
        limit: int | None = None,
    ) -> list[Message]: ...


@runtime_checkable
class TaskRepository(Protocol):
    """Persist provider-neutral task records."""

    async def get(self, id: str) -> Task | None: ...
    async def save(self, task: Task) -> Task: ...


@runtime_checkable
class ApprovalRepository(Protocol):
    """Persist approval decision artifacts."""

    async def get(self, id: str) -> Approval | None: ...
    async def save(self, approval: Approval) -> Approval: ...
    async def list_by_run(self, run_id: str) -> list[Approval]: ...


@runtime_checkable
class RunRepository(Protocol):
    """Persist run records."""

    async def create(self, run: Run) -> Run: ...
    async def get(self, run_id: str) -> Run | None: ...
    async def load_latest_state(self, run_id: str) -> Run | None: ...
    async def update_state(
        self,
        run_id: str,
        new_state: str,
        terminal_seq: int | None,
    ) -> Run: ...


@runtime_checkable
class RunEventRepository(Protocol):
    """Append-only event log for a single run (RT-002)."""

    async def append(self, event: RunEvent) -> RunEvent: ...
    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[RunEvent]: ...
    async def latest_seq(self, run_id: str) -> int: ...


@runtime_checkable
class WorkspaceManifestRepository(Protocol):
    """Persist RT-001 workspace manifests."""

    async def save(self, manifest: WorkspaceManifest) -> WorkspaceManifest: ...
    async def get(self, run_id: str) -> WorkspaceManifest | None: ...


@runtime_checkable
class CheckpointRepository(Protocol):
    """Persist RT-002 checkpoint records."""

    async def get(self, id: str) -> Checkpoint | None: ...
    async def save(self, checkpoint: Checkpoint) -> Checkpoint: ...
    async def list_by_run(self, run_id: str) -> list[Checkpoint]: ...
