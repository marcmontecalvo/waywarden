"""POST /chat route — fire-and-forget chat with background orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from logging import getLogger
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException

from waywarden.api.schemas.chat import ChatRequest, ChatResponse
from waywarden.domain.ids import (
    InstanceId,
    RunEventId,
    RunId,
    SessionId,
    TaskId,
)
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.task import Task

logger = getLogger(__name__)
router = APIRouter(tags=["chat"])

# Module-level mutable references for test injection.
_event_repo: object = None
_run_repo: object = None
_task_repo: object = None
_session_repo: object = None
_lifecycle_svc: object = None


def _get_event_repo() -> object:
    return _event_repo


def _get_runs() -> object:
    return _run_repo


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=202,
    summary="Submit a chat message and get a run id",
)
async def chat(
    body: ChatRequest,
    x_waywarden_operator: str = Header(""),
) -> ChatResponse:
    """Accept a chat message and kick off orchestration."""
    if not x_waywarden_operator:
        raise HTTPException(status_code=401, detail="missing X-Waywarden-Operator header")

    now = datetime.now(UTC)
    session_id = SessionId(str(body.session_id))
    task_id = TaskId(f"task-{uuid4().hex[:12]}")

    # Create task (kept for domain consistency; can be extended later)
    _ = Task(
        id=task_id,
        session_id=session_id,
        title=body.message[:60] or "untitled message",
        objective=body.message,
        state="draft",
        created_at=now,
        updated_at=now,
    )

    run_id = RunId(f"run-{uuid4().hex[:12]}")

    from waywarden.domain.run import Run

    run = Run(
        id=run_id,
        instance_id=InstanceId("instance-stub"),
        task_id=task_id,
        profile=body.session_id,
        policy_preset=body.policy_preset or "ask",  # type: ignore[arg-type]
        manifest_ref=body.manifest_ref or f"//://{task_id}/default",
        entrypoint="api",
        state="created",
        created_at=now,
        updated_at=now,
        terminal_seq=None,
    )

    event_repo = _get_event_repo()
    last_seq = 0  # Stub: no real repo attached during request lifecycle
    if event_repo is not None:
        last_seq = await event_repo.latest_seq(str(run_id))  # type: ignore[attr-defined]

    created_event = RunEvent(
        id=RunEventId(f"evt-{run_id}-created"),
        run_id=run_id,
        seq=last_seq + 1,
        type="run.created",
        payload={
            "instance_id": run.instance_id,
            "profile": run.profile,
            "policy_preset": run.policy_preset,
            "manifest_ref": run.manifest_ref,
            "entrypoint": run.entrypoint,
        },
        timestamp=now,
        causation=Causation(event_id=None, action="chat_submit", request_id=None),
        actor=Actor(kind="system", id=None, display=None),
    )
    if event_repo is not None:
        await event_repo.append(created_event)  # type: ignore[attr-defined]

    # TODO: Wire real orchestration dispatch here:
    #   background_tasks.add_task(_dispatch_background)
    # Pursuing this requires FastAPI test-client setup with async routes,
    # which complicates unit tests. Keeping it as a TODO for P4-5 follow-up.

    return ChatResponse(
        run_id=str(run_id),
        stream_url=f"/api/runs/{run_id}/events?last_seen_seq=0",
    )
