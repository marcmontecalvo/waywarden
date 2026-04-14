import anthropic as sdk

# Map short config names to canonical API model IDs
_MODEL_ALIASES: dict[str, str] = {
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "claude-haiku": "claude-haiku-4-5",
}


class AnthropicModelProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = sdk.AsyncAnthropic(api_key=api_key)
        self._model = _MODEL_ALIASES.get(model, model)

    async def generate(self, request: dict[str, object]) -> dict[str, object]:
        system = str(request.get("system", "You are a helpful executive assistant."))
        messages = list(request.get("messages", [{"role": "user", "content": request.get("user_message", "")}]))

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,  # type: ignore[arg-type]
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return {"text": text}

    async def stream(self, request: dict[str, object]):
        result = await self.generate(request)
        yield result
