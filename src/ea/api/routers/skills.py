from fastapi import APIRouter

from ea.skills.registry import SkillRegistry

router = APIRouter(prefix="/skills", tags=["skills"])
registry = SkillRegistry.default()


@router.get("")
async def list_skills() -> dict[str, list[dict[str, str]]]:
    return {"items": [skill.as_dict() for skill in registry.skills.values()]}
