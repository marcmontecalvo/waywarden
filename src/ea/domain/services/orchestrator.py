from dataclasses import dataclass

from ea.domain.services.context_builder import ContextBuilder
from ea.domain.services.response_planner import ResponsePlanner
from ea.skills.registry import SkillRegistry


@dataclass(slots=True)
class OrchestratorResult:
    reply: str
    skill: str


class Orchestrator:
    def __init__(self) -> None:
        self.registry = SkillRegistry.default()
        self.planner = ResponsePlanner()
        self.context_builder = ContextBuilder()

    async def handle_message(
        self,
        *,
        session_id: str,
        message: str,
        session_repo=None,
    ) -> OrchestratorResult:
        skill = self.registry.pick_skill(message)
        context = await self.context_builder.build(session_id=session_id, message=message)

        if session_repo is not None:
            await session_repo.get_or_create(session_id)

        reply = await self.planner.plan_reply(
            session_id=session_id,
            message=message,
            skill_name=skill.name,
            context=context,
        )
        return OrchestratorResult(reply=reply, skill=skill.name)
