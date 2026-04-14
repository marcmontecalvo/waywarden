from ea.adapters.models.anthropic import AnthropicModelProvider
from ea.adapters.models.openai import OpenAIModelProvider
from ea.domain.services.model_router import ModelRouter
from ea.settings import settings

_SKILL_SYSTEM_PROMPTS: dict[str, str] = {
    "project_manager": (
        "You are a project manager assistant. Help track tasks, priorities, and blockers. "
        "Be concise and action-oriented."
    ),
    "inbox_triage": (
        "You are an inbox assistant. Summarise incoming messages and propose clear, brief replies. "
        "Flag anything requiring urgent attention."
    ),
    "scheduler": (
        "You are a scheduling assistant. Parse natural-language time constraints and suggest "
        "concrete calendar actions. Always confirm details before booking."
    ),
    "briefing": (
        "You are a briefing assistant. Produce a concise daily digest covering tasks, calendar, "
        "and anything noteworthy from recent activity."
    ),
    "coding_handoff": (
        "You are a coding handoff assistant. Package work descriptions clearly for a separate "
        "coding runtime. Summarise the goal, context, and acceptance criteria."
    ),
    "ha_gateway": (
        "You are a home automation assistant. Route approved requests to Home Assistant. "
        "Read-only queries are auto-allowed; write operations require explicit approval."
    ),
}

_DEFAULT_SYSTEM = "You are Waywarden, a helpful executive assistant."


class ResponsePlanner:
    def __init__(self) -> None:
        self._router = ModelRouter()
        self._providers: dict[str, AnthropicModelProvider | OpenAIModelProvider] = {}

    def _get_provider(self, provider_name: str, model: str) -> AnthropicModelProvider | OpenAIModelProvider:
        key = f"{provider_name}:{model}"
        if key not in self._providers:
            if provider_name == "anthropic":
                self._providers[key] = AnthropicModelProvider(
                    api_key=settings.anthropic_api_key, model=model
                )
            else:
                self._providers[key] = OpenAIModelProvider(
                    api_key=settings.openai_api_key, model=model
                )
        return self._providers[key]

    async def plan_reply(
        self,
        *,
        session_id: str,
        message: str,
        skill_name: str,
        context: dict[str, object] | None = None,
    ) -> str:
        profile = self._router.get_profile(skill_name)
        provider = self._get_provider(profile["provider"], profile["model"])

        system = _SKILL_SYSTEM_PROMPTS.get(skill_name, _DEFAULT_SYSTEM)

        # Inject memory/knowledge snippets into system when available (Phase 2 will populate these)
        if context:
            memory_items = context.get("memory", [])
            knowledge_items = context.get("knowledge", [])
            if memory_items:
                snippets = "\n".join(f"- {m}" for m in memory_items)
                system += f"\n\nRecent memory:\n{snippets}"
            if knowledge_items:
                snippets = "\n".join(f"- {k}" for k in knowledge_items)
                system += f"\n\nRelevant knowledge:\n{snippets}"

        request: dict[str, object] = {
            "system": system,
            "messages": [{"role": "user", "content": message}],
        }

        result = await provider.generate(request)
        return str(result["text"])
