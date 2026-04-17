from fastapi import APIRouter

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/health")
async def memory_health() -> dict[str, str]:
    return {"provider": "stub", "status": "ok"}
