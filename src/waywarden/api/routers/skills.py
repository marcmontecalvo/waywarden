from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from waywarden.domain.services.skill_registry import SkillRegistry

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills(request: Request) -> JSONResponse:
    registry = getattr(request.app.state, "skill_registry", None)
    if not isinstance(registry, SkillRegistry):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "feature": "skills",
                "placeholder": True,
                "message": (
                    "No skill registry is loaded in this app instance yet. "
                    "Inject a profile-backed registry before treating this route as active."
                ),
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "placeholder",
            "feature": "skills",
            "placeholder": True,
            "message": (
                "This route exposes static profile scaffolding only. "
                "Listing a skill here does not imply runtime execution is ready."
            ),
            "items": [skill.as_dict() for skill in registry.skills.values()],
        },
    )
