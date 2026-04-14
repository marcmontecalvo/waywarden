import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ea.adapters.db.repositories.session_repo import SessionRepository
from ea.adapters.db.session import get_db
from ea.api.schemas.chat import ChatRequest, ChatResponse
from ea.domain.services.orchestrator import Orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])
orchestrator = Orchestrator()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    session_repo = SessionRepository(db)
    result = await orchestrator.handle_message(
        session_id=session_id,
        message=request.message,
        session_repo=session_repo,
    )
    return ChatResponse(session_id=session_id, reply=result.reply, skill=result.skill)
