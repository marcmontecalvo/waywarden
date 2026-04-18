from waywarden.domain.services.skill import Skill
from waywarden.domain.services.skill_registry import SkillRegistry


def build_ea_skill_registry() -> SkillRegistry:
    skills = [
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
    registry = SkillRegistry(skills=skills, default_skill="project_manager")
    registry.add_rule(("email", "inbox"), "inbox_triage")
    registry.add_rule(("calendar", "schedule"), "scheduler")
    registry.add_rule(("code", "repo"), "coding_handoff")
    registry.add_rule(("home assistant", "lights", "thermostat"), "ha_gateway")
    registry.add_rule(("brief", "summary"), "briefing")
    return registry
