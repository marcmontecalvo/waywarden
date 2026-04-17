from waywarden.todo.ea_profile.skills.registry import SkillRegistry


def test_pick_default_skill() -> None:
    registry = SkillRegistry.default()
    skill = registry.pick_skill("Help me stay on top of my projects")
    assert skill.name == "project_manager"
