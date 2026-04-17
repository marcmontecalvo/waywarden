class ResponsePlanner:
    async def plan_reply(self, *, session_id: str, message: str, skill_name: str) -> str:
        return f"[{skill_name}] Placeholder reply for: {message}"
