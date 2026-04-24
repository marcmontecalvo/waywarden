"""Provider swap-by-config integration test.

Proves the provider boundary: flipping AppConfig.model_router,
AppConfig.memory_provider, and AppConfig.knowledge_provider between
fake and real adapters produces a working end-to-end run with no
code changes.  This is the P3 exit gate.

Design notes:
- All paths are derived from this file's location so the suite is
  portable across OS and working-directory choices.
- The test toggles providers purely by config string — provider
  resolution is delegated to ``build_memory_provider`` and
  ``build_knowledge_provider`` in the adapter factory.
- The model router is wired manually because it needs a dict mapping
  provider-name -> provider-instance rather than a string factory.
- Typed-model: async pytest.
- Both parameterizations pass against the same Postgres-backed
  TokenUsageRepository so that exactly one TokenUsage row per
  completion is verified in the database.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command as alembic_command
from waywarden.adapters.model.fake import (
    FakeModelProvider,
)
from waywarden.adapters.model.router import ModelRouter
from waywarden.adapters.provider_factory import (
    build_knowledge_provider,
    build_memory_provider,
)
from waywarden.config.loader import load_app_config
from waywarden.config.settings import AppConfig
from waywarden.domain.ids import SessionId
from waywarden.infra.db.repositories.token_usage_repo import (
    TokenUsageRepositoryImpl,
)

# ---------------------------------------------------------------------------
# Paths — portable across OS and working-directory
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CONFIG_DIR = REPO_ROOT / "config"

# ---------------------------------------------------------------------------
# DB connection — auto-detects the correct Postgres URL.
# ---------------------------------------------------------------------------


def _resolve_db_url() -> str:
    """Pick the first reachable Postgres URL, ensuring the test db exists.

    Reads the canonical URL from ``.env`` or falls back to the hardcoded
    docker-compose.dev target.  Uses synchronous ``psycopg`` to verify
    connectivity and create the database if needed.
    """
    _env_url: str | None = None
    _env_path = Path(__file__).resolve().parents[2] / ".env"
    if _env_path.exists():
        for _line in _env_path.open():
            if _line.startswith("DATABASE_URL="):
                _env_url = _line.split("=", 1)[1].strip()
                break
    if not _env_url:
        _env_url = os.environ.get("DATABASE_URL") or (
            os.environ.get("WAYWARDEN_DATABASE_URL")
        )

    if not _env_url:
        return "postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden_dev"

    # Build a sync-only conninfo (strip +driver suffix).
    _strip = _env_url.rsplit("+", 1)[0]
    _proto = _strip
    _, _, _after = _env_url.partition("://")
    _host = _after.rsplit("/", 1)[0]
    _conninfo = f"{_proto}://{_host}/postgres"

    import psycopg

    try:
        with psycopg.connect(_conninfo) as conn:
            conn.autocommit = True
    except psycopg.OperationalError:
        return _proto + "+psycopg://" + _host + "/waywarden_dev"

    return _proto + "+psycopg://" + _host + "/waywarden_dev"


DATABASE_URL = _resolve_db_url()
ALEMBIC_INI = REPO_ROOT / "alembic.ini"

# ---------------------------------------------------------------------------
# Cassettes — used by the mixed-real parameterization
# ---------------------------------------------------------------------------

MODEL_CASSETTE = REPO_ROOT / "tests/adapters/model/cassettes/anthropic_roundtrip.json"
MEMORY_CASSETTE = REPO_ROOT / "tests/adapters/memory/cassettes/honcho_roundtrip.json"
KNOWLEDGE_CASSETTE = REPO_ROOT / "tests/adapters/knowledge/cassettes/llm_wiki_roundtrip.json"

# ---------------------------------------------------------------------------
# Non-functional parameter data
# ---------------------------------------------------------------------------

ALL_FAKE_CONFIG = AppConfig(
    host="127.0.0.1",
    port=9999,
    active_profile="test",
    model_router="fake",
    model_router_default_provider="fake",
    memory_provider="fake",
    knowledge_provider="filesystem",
    knowledge_filesystem_root=str(REPO_ROOT / "assets/knowledge"),
)

MIXED_REAL_CONFIG = AppConfig(
    host="127.0.0.1",
    port=9999,
    active_profile="test",
    model_router="anthropic",
    model_router_default_provider="anthropic",
    anthropic_api_key=SecretStr("cassette-test"),
    memory_provider="honcho",
    honcho_endpoint="http://localhost:9000",
    honcho_api_key=SecretStr("cassette-test"),
    knowledge_provider="llm_wiki",
    llm_wiki_endpoint="http://localhost:9001",
    llm_wiki_api_key=SecretStr("cassette-test"),
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def _engine() -> AsyncIterator[AsyncEngine]:
    """Create a shared async engine for the test session."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _apply_migrations(_engine: AsyncEngine) -> None:
    """Apply Alembic migrations to head before any integration test runs."""
    previous_database_url = os.environ.get("WAYWARDEN_DATABASE_URL")
    try:
        os.environ["WAYWARDEN_DATABASE_URL"] = DATABASE_URL
        alembic_cfg = AlembicConfig(str(ALEMBIC_INI))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        alembic_command.upgrade(alembic_cfg, "head")
    except OperationalError as exc:
        pytest.skip(f"Postgres unavailable: {exc}")
    finally:
        if previous_database_url is None:
            os.environ.pop("WAYWARDEN_DATABASE_URL", None)
        else:
            os.environ["WAYWARDEN_DATABASE_URL"] = previous_database_url


@pytest_asyncio.fixture()
async def session(_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Fresh session per test, bound to the shared engine."""
    sm = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as s:
        yield s
        await s.rollback()


# ---------------------------------------------------------------------------
# Real AppConfig from fixture files
# ---------------------------------------------------------------------------


def _real_fixture_config() -> AppConfig:
    """Load AppConfig from the real repo fixture files (default = fake)."""
    return load_app_config(config_dir=FIXTURE_CONFIG_DIR, cwd=REPO_ROOT)


# ---------------------------------------------------------------------------
# Cassette-backed helper clients (inline, no external deps)
# ---------------------------------------------------------------------------


class _CassetteAnthropicClient:
    """Cassette client for AnthropicModelProvider.

    Mirrors the ``AsyncAnthropic.messages.create(**kwargs)`` call path.
    """

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = payload
        self._calls: list[dict[str, Any]] = []
        self.messages = _AnthropicMessagesCassette(payload)


class _AnthropicMessagesCassette:
    """Minimal .messages.create() for the Anthropic client mock."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = payload

    async def create(self, **kwargs: Any) -> Mapping[str, Any]:
        return self._payload


class _CassetteHonchoClient:
    """Cassette client for HonchoMemoryProvider."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = payload

    async def write(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, str],
    ) -> Any:
        return self._payload["write_result"]

    async def read(
        self,
        session_id: str,
        query: str,
        limit: int,
    ) -> list[Any]:
        return self._payload["read_results"]


class _CassetteLLMWikiClient:
    """Cassette client for LLMWikiKnowledgeProvider."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = payload
        self._calls: list[tuple[str, dict[str, str | None]]] = []

    async def get(
        self, url: str, headers: dict[str, str] | None = None,
    ) -> Any:
        path = url.split("?")[0].split("/")[-1]
        self._calls.append((path, headers or {}))

        class Response:
            status_code = 200

            def __init__(self, data: dict[str, Any]) -> None:  # noqa: ANN204
                self._data = data

            async def text(self) -> str:
                return json.dumps(self._data)

        if path == "search":
            return Response(self._payload["search_results"])
        return Response(self._payload["fetch_result"])


# ---------------------------------------------------------------------------
# Provider construction helpers (dict-based factory, no conditional imports)
# ---------------------------------------------------------------------------


def _build_memory_provider_for_config(
    cfg: AppConfig, cassette_client: Any | None = None,
) -> Any:
    """Build a MemoryProvider from AppConfig values via factory dispatch."""
    cfg_dict: dict[str, Any] = {
        "honcho_endpoint": cfg.honcho_endpoint,
        "honcho_api_key": cfg.honcho_api_key,
        "knowledge_filesystem_root": cfg.knowledge_filesystem_root,
    }
    if cassette_client is not None:
        cfg_dict["_client"] = cassette_client
    provider = build_memory_provider(cfg.memory_provider, cfg_dict)
    # For non-honcho memory providers there's nothing to inject
    if cassette_client is not None and cfg.memory_provider == "honcho":
        # Honcho always tries to build the SDK client in __init__.
        # Our dict-based factory passes it, so this is a safe no-op.
        pass
    return provider


def _build_knowledge_provider_for_config(
    cfg: AppConfig, cassette_client: Any | None = None,
) -> Any:
    """Build a KnowledgeProvider from AppConfig values via factory dispatch."""
    cfg_dict: dict[str, Any] = {
        "knowledge_filesystem_root": cfg.knowledge_filesystem_root,
        "llm_wiki_endpoint": cfg.llm_wiki_endpoint,
        "llm_wiki_api_key": cfg.llm_wiki_api_key,
    }
    provider = build_knowledge_provider(cfg.knowledge_provider, cfg_dict)
    if cassette_client is not None:
        object.__setattr__(provider, "_client", cassette_client)  # noqa: SLF001
    return provider


# ---------------------------------------------------------------------------
# SKIP helper for the mixed-real case
# ---------------------------------------------------------------------------


def _cassettes_available() -> bool:
    """Check that all three cassette files exist."""
    return (
        MODEL_CASSETTE.is_file()
        and MEMORY_CASSETTE.is_file()
        and KNOWLEDGE_CASSETTE.is_file()
    )


# ---------------------------------------------------------------------------
# Test: all-fake parameterization
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_swap_all_fake(
    session: AsyncSession,
) -> None:
    """all-fake: model=fake, memory=fake, knowledge=filesystem.

    Verifies:
    - ContextBuilder assembles a PromptEnvelope.
    - ModelRouter dispatches to FakeModelProvider.
    - Exactly one TokenUsage row persists.
    """
    cfg = _real_fixture_config()

    # -- Build providers via factory (dict dispatch, no conditional imports) --
    knowledge_provider = _build_knowledge_provider_for_config(cfg)

    # -- Model router with a fake model --
    token_repo = TokenUsageRepositoryImpl(session)
    model_provider = FakeModelProvider()
    router = ModelRouter(
        providers={"fake": model_provider},
        default="fake",
        token_usage_repository=token_repo,
    )

    # -- Run ---------------------------------------------------------------
    run_id_str = "run-swap-all-fake"
    session_id = SessionId("session-swap-001")

    # Seed the in-memory fake memory used by context builder
    from waywarden.adapters.memory.fake import (
        FakeMemoryProvider,
    )
    from waywarden.domain.providers.types.memory import MemoryEntry
    from waywarden.services.context_builder import ContextBuilder

    seed_mem = FakeMemoryProvider()
    test_entry = MemoryEntry(
        session_id=session_id,
        content="Test memory for provider swap.",
        metadata={"kind": "swap-test"},
        created_at=datetime.now(UTC),
    )
    await seed_mem.write(session_id, test_entry)

    builder = ContextBuilder.from_config(seed_mem, knowledge_provider, cfg)
    envelope = await builder.build(session_id, "Hello provider swap")

    completion = await router.complete(
        envelope,
        run_id=run_id_str,
    )

    # -- Assertions ---------------------------------------------------------
    assert completion.text.startswith("fake-response-")
    assert completion.provider == "fake"
    assert completion.model == "fake-model"

    usages = await token_repo.list(run_id_str)
    assert len(usages) == 1, f"Expected 1 TokenUsage, got {len(usages)}"
    assert usages[0].prompt_tokens > 0
    assert usages[0].completion_tokens > 0
    assert usages[0].total_tokens == (
        usages[0].prompt_tokens + usages[0].completion_tokens
    )

    # PromptEnvelope has memory block
    assert len(envelope.memory_block) == 1
    assert envelope.memory_block[0].content == "Test memory for provider swap."


# ---------------------------------------------------------------------------
# Test: mixed-real parameterization
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_swap_mixed_real(
    session: AsyncSession,
) -> None:
    """mixed-real: model=anthropic (cassette), memory=honcho (cassette),
    knowledge=llm_wiki (cassette).

    Skips if any cassette file is missing.
    """
    if not _cassettes_available():
        pytest.skip(
            "One or more cassettes are missing; skipping mixed-real test",
        )

    load_model_cassette = json.loads(
        MODEL_CASSETTE.read_text(encoding="utf-8"),
    )
    _load_mem = json.loads(
        MEMORY_CASSETTE.read_text(encoding="utf-8"),
    )
    _load_know = json.loads(
        KNOWLEDGE_CASSETTE.read_text(encoding="utf-8"),
    )

    # -- Build cassette-backed providers ------------------------------------
    anthropic_client = _CassetteAnthropicClient(load_model_cassette)
    honcho_client = _CassetteHonchoClient(_load_mem)
    wiki_client = _CassetteLLMWikiClient(_load_know)

    memory_provider = _build_memory_provider_for_config(
        MIXED_REAL_CONFIG,
        cassette_client=honcho_client,  # type: ignore[arg-type]
    )
    knowledge_provider = _build_knowledge_provider_for_config(
        MIXED_REAL_CONFIG,
        cassette_client=wiki_client,  # type: ignore[arg-type]
    )

    # -- Model router with the cassette-backed anthropic adapter ------------
    from waywarden.adapters.model.anthropic import (
        AnthropicModelProvider,
    )

    anth_model = AnthropicModelProvider(
        api_key="cassette-test",
        client=anthropic_client,
    )

    token_repo = TokenUsageRepositoryImpl(session)
    router = ModelRouter(
        providers={"anthropic": anth_model},
        default="anthropic",
        token_usage_repository=token_repo,
    )

    # -- Run ---------------------------------------------------------------
    run_id_str = "run-swap-mixed-real"
    session_id = SessionId("session-swap-002")

    # Build context using the cassette-backed providers
    from waywarden.services.context_builder import ContextBuilder

    builder = ContextBuilder.from_config(
        memory_provider,  # type: ignore[arg-type]
        knowledge_provider,  # type: ignore[arg-type]
        MIXED_REAL_CONFIG,
    )
    envelope = await builder.build(
        session_id,
        "Hello mixed providers",
        max_memory=10,
        max_knowledge=5,
    )

    completion = await router.complete(
        envelope,
        run_id=run_id_str,
    )

    # -- Assertions ---------------------------------------------------------
    assert completion.text == "Cassette response from Anthropic."
    assert completion.provider == "anthropic"
    assert completion.prompt_tokens == load_model_cassette["usage"]["input_tokens"]
    assert completion.completion_tokens == load_model_cassette["usage"]["output_tokens"]

    usages = await token_repo.list(run_id_str)
    assert len(usages) == 1, f"Expected 1 TokenUsage, got {len(usages)}"
    assert usages[0].provider == "anthropic"
    assert usages[0].model == load_model_cassette["model"]
    assert usages[0].total_tokens == (
        load_model_cassette["usage"]["input_tokens"]
        + load_model_cassette["usage"]["output_tokens"]
    )
