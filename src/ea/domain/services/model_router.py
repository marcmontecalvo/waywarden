class ModelRouter:
    def get_profile(self, skill_name: str) -> str:
        mapping = {
            "inbox_triage": "inbox_triage",
            "scheduler": "scheduler",
            "briefing": "briefing",
        }
        return mapping.get(skill_name, "default_chat")
