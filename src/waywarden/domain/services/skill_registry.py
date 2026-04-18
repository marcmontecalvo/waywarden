from waywarden.domain.services.skill import Skill


class SkillRegistry:
    def __init__(self, skills: list[Skill], default_skill: str) -> None:
        if default_skill not in {s.name for s in skills}:
            raise ValueError(f"default_skill {default_skill!r} not in provided skills")
        self.skills = {skill.name: skill for skill in skills}
        self._default_skill = default_skill
        self._rules: list[tuple[tuple[str, ...], str]] = []

    def add_rule(self, keywords: tuple[str, ...], skill_name: str) -> None:
        if skill_name not in self.skills:
            raise ValueError(f"skill {skill_name!r} not registered")
        self._rules.append((keywords, skill_name))

    def pick_skill(self, message: str) -> Skill:
        lowered = message.lower()
        for keywords, skill_name in self._rules:
            if any(keyword in lowered for keyword in keywords):
                return self.skills[skill_name]
        return self.skills[self._default_skill]
