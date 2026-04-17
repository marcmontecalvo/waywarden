import uuid

from fastapi import APIRouter

from ea.api.schemas.chat import ChatRequest, ChatResponse
from ea.domain.services.orchestrator import Orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])
orchestrator = Orchestrator()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    result = await orchestrator.handle_message(session_id=session_id, message=request.message)
    return ChatResponse(session_id=session_id, reply=result.reply, skill=result.skill)
