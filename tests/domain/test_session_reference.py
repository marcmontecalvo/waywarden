"""Tests for coding-session continuity session reference model (P6-3 #94).

Tests cover:
- Domain model: field validation, composite key, timestamp default
- Repository protocol: mock-based unit tests for create, retrieve, prune,
  and missing-artifact paths
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from waywarden.domain.session_reference import SessionReference

# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------


def test_session_reference_requires_non_empty_fields() -> None:
    """Empty run_id, artifact_id, or session_ref raises ValueError."""
    with pytest.raises(ValueError, match="run_id"):
        SessionReference(run_id="", artifact_id="a", session_ref="s")
    with pytest.raises(ValueError, match="artifact_id"):
        SessionReference(run_id="r", artifact_id="", session_ref="s")
    with pytest.raises(ValueError, match="session_ref"):
        SessionReference(run_id="r", artifact_id="a", session_ref="")


def test_session_reference_has_composite_key() -> None:
    ref = SessionReference(run_id="run-1", artifact_id="art-1", session_ref="msg-1")
    assert ref.composite_key == "run-1:art-1"


def test_session_reference_created_at_defaults_to_utc() -> None:
    ref = SessionReference(run_id="r", artifact_id="a", session_ref="s")
    assert ref.created_at.tzinfo is not None


def test_session_reference_is_frozen() -> None:
    ref = SessionReference(run_id="r", artifact_id="a", session_ref="s")
    with pytest.raises((AttributeError, TypeError)):
        ref.run_id = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Mock-based repository protocol tests
# -----------------------------------------------------------------------


class _InMemorySessionRefRepo:
    """In-memory implementation of SessionRefRepository for unit testing."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], SessionReference] = {}

    async def create(self, ref: SessionReference) -> SessionReference:
        key = (ref.run_id, ref.artifact_id)
        self._store[key] = ref
        return ref

    async def get_by_run(self, run_id: str) -> list[SessionReference]:
        return [r for (r_id, _a_id), r in self._store.items() if r_id == run_id]

    async def get_by_artifact(self, artifact_id: str) -> list[SessionReference]:
        return [r for (_r_id, a_id), r in self._store.items() if a_id == artifact_id]

    async def get_by_key(self, run_id: str, artifact_id: str) -> SessionReference | None:
        return self._store.get((run_id, artifact_id))

    async def remove(self, run_id: str) -> int:
        result = [k for k in self._store if k[0] == run_id]
        for k in result:
            del self._store[k]
        return len(result)


def _repo() -> _InMemorySessionRefRepo:
    return _InMemorySessionRefRepo()


@pytest.fixture()
async def repo() -> _InMemorySessionRefRepo:
    return _repo()


# -----------------------------------------------------------------------
# Repository protocol — create
# -----------------------------------------------------------------------


@pytest.fixture
async def fresh_repo() -> _InMemorySessionRefRepo:
    return _repo()


async def test_create_persists_reference(
    fresh_repo: _InMemorySessionRefRepo,
) -> None:
    """Create stores a new reference under its composite key."""
    ref = SessionReference(
        run_id="run-1",
        artifact_id="art-1",
        session_ref="msg-1",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    await fresh_repo.create(ref)
    found = await fresh_repo.get_by_key("run-1", "art-1")
    assert found is not None
    assert found.run_id == "run-1"
    assert found.session_ref == "msg-1"


# -----------------------------------------------------------------------
# Repository protocol — retrieve by key (missing artifact)
# -----------------------------------------------------------------------


async def test_retrieve_missing_key_returns_none(
    repo: _InMemorySessionRefRepo,
) -> None:
    """Non-existent composite key returns None."""
    found = await repo.get_by_key("run-missing", "art-missing")
    assert found is None


# -----------------------------------------------------------------------
# Repository protocol — retrieve by run
# -----------------------------------------------------------------------


async def test_list_by_run_returns_all(
    repo: _InMemorySessionRefRepo,
) -> None:
    """Multiple references tied to the same run are all returned."""
    for i in range(3):
        await repo.create(
            SessionReference(
                run_id="run-A",
                artifact_id=f"art-{i}",
                session_ref=f"msg-{i}",
            )
        )
    by_run = await repo.get_by_run("run-A")
    assert len(by_run) == 3


# -----------------------------------------------------------------------
# Repository protocol — retrieve by artifact
# -----------------------------------------------------------------------


async def test_list_by_artifact_returns_all(
    repo: _InMemorySessionRefRepo,
) -> None:
    """Cross-run references to the same artifact are returned."""
    await repo.create(
        SessionReference(
            run_id="run-1",
            artifact_id="shared",
            session_ref="msg-1",
        )
    )
    await repo.create(
        SessionReference(
            run_id="run-2",
            artifact_id="shared",
            session_ref="msg-2",
        )
    )
    by_artifact = await repo.get_by_artifact("shared")
    assert len(by_artifact) == 2


# -----------------------------------------------------------------------
# Repository protocol — prune / remove
# -----------------------------------------------------------------------


async def test_prune_removes_all_for_run(
    repo: _InMemorySessionRefRepo,
) -> None:
    """Remove deletes all references for a run and returns count."""
    for i in range(3):
        await repo.create(
            SessionReference(
                run_id="run-delete",
                artifact_id=f"art-{i}",
                session_ref=f"msg-{i}",
            )
        )
    removed = await repo.remove("run-delete")
    remaining = await repo.get_by_run("run-delete")
    assert removed == 3
    assert len(remaining) == 0


async def test_prune_empty_run_returns_zero(
    repo: _InMemorySessionRefRepo,
) -> None:
    """Pruning a run with no references returns 0."""
    removed = await repo.remove("nonexistent")
    assert removed == 0
