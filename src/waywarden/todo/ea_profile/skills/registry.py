from waywarden.todo.ea_profile.skills.base import Skill


class SkillRegistry:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = {skill.name: skill for skill in skills}

    @classmethod
    def default(cls) -> "SkillRegistry":
        return cls(
            skills=[
                Skill(
                    "project_manager",
                    "Tracks tasks, next steps, blockers, and priorities.",
                    "default_chat",
                ),
                Skill(
                    "inbox_triage",
                    "Summarizes inbox and proposes replies.",
                    "inbox_triage",
                ),
                Skill(
                    "scheduler",
                    "Understands calendar constraints and proposes scheduling actions.",
                    "scheduler",
                ),
                Skill("briefing", "Builds daily and weekly briefings.", "briefing"),
                Skill(
                    "coding_handoff",
                    "Packages work for the external coding runtime.",
                    "default_chat",
                ),
                Skill(
                    "ha_gateway",
                    "Routes approved requests to the external HA runtime.",
                    "default_chat",
                ),
            ]
        )

    def pick_skill(self, message: str) -> Skill:
        lowered = message.lower()
        if "email" in lowered or "inbox" in lowered:
            return self.skills["inbox_triage"]
        if "calendar" in lowered or "schedule" in lowered:
            return self.skills["scheduler"]
        if "code" in lowered or "repo" in lowered:
            return self.skills["coding_handoff"]
        if "home assistant" in lowered or "lights" in lowered or "thermostat" in lowered:
            return self.skills["ha_gateway"]
        if "brief" in lowered or "summary" in lowered:
            return self.skills["briefing"]
        return self.skills["project_manager"]
