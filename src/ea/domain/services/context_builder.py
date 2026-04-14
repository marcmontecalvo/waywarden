class ContextBuilder:
    async def build(self, *, session_id: str, message: str) -> dict[str, object]:
        return {
            "session_id": session_id,
            "message": message,
            "memory": [],
            "knowledge": [],
            "tasks": [],
        }
