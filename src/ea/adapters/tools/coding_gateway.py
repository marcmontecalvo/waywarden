class CodingGatewayTool:
    async def invoke(self, call: dict[str, object]) -> dict[str, object]:
        return {"status": "stub", "tool": "coding_gateway"}
