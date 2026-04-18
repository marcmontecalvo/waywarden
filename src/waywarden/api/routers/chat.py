import uuid

from fastapi import APIRouter, Request

from waywarden.api.schemas.chat import ChatRequest, ChatResponse
from waywarden.domain.services.orchestrator import Orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    orchestrator: Orchestrator = http_request.app.state.orchestrator
    session_id = request.session_id or str(uuid.uuid4())
    result = await orchestrator.handle_message(session_id=session_id, message=request.message)
    return ChatResponse(session_id=session_id, reply=result.reply, skill=result.skill)
