class ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def register(self, name: str, tool: object) -> None:
        self.tools[name] = tool
