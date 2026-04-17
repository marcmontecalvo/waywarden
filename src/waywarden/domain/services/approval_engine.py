class ApprovalEngine:
    def classify(self, tool_name: str) -> str:
        if tool_name in {"knowledge.search", "memory.read", "tasks.create", "ha.read"}:
            return "auto_allow"
        if tool_name in {
            "gmail.send",
            "calendar.create_event",
            "calendar.update_event",
            "shell.exec",
            "coding.start_task",
            "ha.write",
        }:
            return "approval_required"
        return "forbidden"
