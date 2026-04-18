from fastapi import APIRouter, Request

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills(request: Request) -> dict[str, list[dict[str, str]]]:
    registry = request.app.state.skill_registry
    return {"items": [skill.as_dict() for skill in registry.skills.values()]}
