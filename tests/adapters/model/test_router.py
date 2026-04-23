"""Tests for model provider routing and token usage accounting."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.adapters.model.fake import FakeModelProvider
from waywarden.adapters.model.router import ModelRouter
from waywarden.domain.providers.types.model import ModelCompletion, PromptEnvelope
from waywarden.infra.db.repositories.token_usage_repo import TokenUsageRepositoryImpl


class StaticModelProvider:
    def __init__(self, *, name: str, text: str) -> None:
        self.name = name
        self.text = text

    async def complete(
        self,
        prompt: PromptEnvelope,
        *,
        tools: tuple[()] = (),
        stream: bool = False,
    ) -> ModelCompletion:
        return ModelCompletion(
            session_id=prompt.session_id,
            text=self.text,
            model=f"{self.name}-model",
            provider=self.name,
            recorded_at=datetime.now(UTC),
            prompt_tokens=2,
            completion_tokens=3,
            total_tokens=5,
        )


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE token_usage (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    call_ref TEXT,
                    UNIQUE(run_id, seq),
                    CHECK (seq >= 1),
                    CHECK (total_tokens = prompt_tokens + completion_tokens),
                    CHECK (prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0)
                )"""
            )
        )

    async with factory() as db_session:
        yield db_session

    await engine.dispose()


async def test_routes_to_named_provider(session: AsyncSession) -> None:
    usage_repo = TokenUsageRepositoryImpl(session)
    router = ModelRouter(
        providers={
            "fake": StaticModelProvider(name="fake", text="default"),
            "anthropic": StaticModelProvider(name="anthropic", text="selected"),
        },
        default="fake",
        token_usage_repository=usage_repo,
    )
    prompt = PromptEnvelope(session_id="session-1", messages=["hello"])

    completion = await router.complete(prompt, provider="anthropic", run_id="run-1")

    assert completion.text == "selected"
    assert completion.provider == "anthropic"


@pytest.mark.integration
async def test_records_token_usage(session: AsyncSession) -> None:
    usage_repo = TokenUsageRepositoryImpl(session)
    router = ModelRouter(
        providers={"fake": FakeModelProvider()},
        default="fake",
        token_usage_repository=usage_repo,
    )
    prompt = PromptEnvelope(session_id="session-1", messages=["count these tokens"])

    completion = await router.complete(prompt, run_id="run-usage", call_ref="call-001")

    rows = await usage_repo.list("run-usage")
    assert len(rows) == 1
    assert rows[0].provider == completion.provider
    assert rows[0].model == completion.model
    assert rows[0].prompt_tokens == completion.prompt_tokens
    assert rows[0].completion_tokens == completion.completion_tokens
    assert rows[0].total_tokens == completion.total_tokens
    assert rows[0].call_ref == "call-001"
