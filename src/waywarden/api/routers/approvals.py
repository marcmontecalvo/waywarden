from fastapi import APIRouter

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
async def list_approvals() -> dict[str, list[dict[str, str]]]:
    return {"items": []}
