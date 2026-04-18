from dataclasses import dataclass

from waywarden.domain.services.response_planner import ResponsePlanner
from waywarden.domain.services.skill_registry import SkillRegistry


@dataclass(frozen=True, slots=True)
class OrchestratorResult:
    reply: str
    skill: str


class Orchestrator:
    def __init__(self, registry: SkillRegistry, planner: ResponsePlanner | None = None) -> None:
        self.registry = registry
        self.planner = planner or ResponsePlanner()

    async def handle_message(self, *, session_id: str, message: str) -> OrchestratorResult:
        skill = self.registry.pick_skill(message)
        reply = await self.planner.plan_reply(
            session_id=session_id, message=message, skill_name=skill.name
        )
        return OrchestratorResult(reply=reply, skill=skill.name)
