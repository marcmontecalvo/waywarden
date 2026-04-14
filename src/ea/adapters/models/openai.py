from openai import AsyncOpenAI


class OpenAIModelProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(self, request: dict[str, object]) -> dict[str, object]:
        system = str(request.get("system", "You are a helpful executive assistant."))
        user_messages = list(request.get("messages", [{"role": "user", "content": request.get("user_message", "")}]))

        messages = [{"role": "system", "content": system}] + user_messages

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
        )
        text = response.choices[0].message.content or ""
        return {"text": text}

    async def stream(self, request: dict[str, object]):
        result = await self.generate(request)
        yield result
