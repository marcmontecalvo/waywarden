"""Tests for metadata registration."""

from waywarden.infra.db.metadata import metadata


def test_all_tables_registered() -> None:
    """All 9 tables must be registered on the shared metadata."""
    expected = {
        "approvals",
        "checkpoints",
        "messages",
        "run_events",
        "runs",
        "sessions",
        "tasks",
        "token_usage",
        "workspace_manifests",
    }
    assert set(metadata.tables.keys()) == expected
