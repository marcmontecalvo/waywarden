class CLIChannel:
    async def receive(self, payload: dict[str, object]) -> dict[str, object]:
        return payload
