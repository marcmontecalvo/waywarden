from fastapi import APIRouter

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/health")
async def knowledge_health() -> dict[str, str]:
    return {"provider": "stub", "status": "ok"}
