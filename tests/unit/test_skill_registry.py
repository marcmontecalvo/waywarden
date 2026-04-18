from waywarden.domain.services.skill import Skill
from waywarden.domain.services.skill_registry import SkillRegistry
from waywarden.profiles.ea.skills.factory import build_ea_skill_registry


def test_ea_registry_pick_default_skill() -> None:
    registry = build_ea_skill_registry()
    skill = registry.pick_skill("Help me stay on top of my projects")
    assert skill.name == "project_manager"


def test_ea_registry_matches_keyword_rule() -> None:
    registry = build_ea_skill_registry()
    assert registry.pick_skill("check my inbox").name == "inbox_triage"
    assert registry.pick_skill("schedule a meeting").name == "scheduler"
    assert registry.pick_skill("brief me").name == "briefing"


def test_registry_rejects_unknown_default() -> None:
    import pytest

    skills = [Skill("a", "desc", "prof")]
    with pytest.raises(ValueError):
        SkillRegistry(skills=skills, default_skill="missing")


def test_registry_rejects_unknown_rule_target() -> None:
    import pytest

    skills = [Skill("a", "desc", "prof")]
    registry = SkillRegistry(skills=skills, default_skill="a")
    with pytest.raises(ValueError):
        registry.add_rule(("x",), "missing")
