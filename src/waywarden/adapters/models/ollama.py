from collections.abc import AsyncIterator


class OllamaModelProvider:
    async def generate(self, request: dict[str, object]) -> dict[str, object]:
        return {"text": "stub"}

    async def stream(self, request: dict[str, object]) -> AsyncIterator[dict[str, object]]:
        yield {"text": "stub"}
