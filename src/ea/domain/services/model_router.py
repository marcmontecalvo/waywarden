# Maps profile name → {provider, model}.
# Mirrors config/models.yaml — update both if profiles change.
_PROFILES: dict[str, dict[str, str]] = {
    "default_chat": {"provider": "openai", "model": "gpt-5.4-thinking"},
    "inbox_triage": {"provider": "anthropic", "model": "claude-sonnet"},
    "scheduler": {"provider": "openai", "model": "gpt-5.4-thinking"},
    "briefing": {"provider": "openai", "model": "gpt-5.4-thinking"},
    "memory_maintenance": {"provider": "openai", "model": "gpt-5.4-thinking"},
    "knowledge_curator": {"provider": "anthropic", "model": "claude-sonnet"},
}

_SKILL_TO_PROFILE: dict[str, str] = {
    "inbox_triage": "inbox_triage",
    "scheduler": "scheduler",
    "briefing": "briefing",
    "memory_maintenance": "memory_maintenance",
    "knowledge_curator": "knowledge_curator",
}


class ModelRouter:
    def get_profile(self, skill_name: str) -> dict[str, str]:
        profile_name = _SKILL_TO_PROFILE.get(skill_name, "default_chat")
        return _PROFILES[profile_name]
