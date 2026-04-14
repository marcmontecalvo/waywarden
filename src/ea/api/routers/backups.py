from fastapi import APIRouter

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post("/run")
async def run_backup() -> dict[str, str]:
    return {"status": "queued"}
