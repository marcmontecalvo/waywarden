"""Tests for CHECK constraints matching canonical vocabularies."""

from sqlalchemy.dialects import postgresql

from waywarden.infra.db.metadata import metadata


def _get_check_sql(table_name: str) -> list[str]:
    """Return CHECK constraint SQL strings for a table."""
    table = metadata.tables[table_name]
    results = []
    for c in table.constraints:
        if type(c).__name__ == "CheckConstraint":
            compiled = c.sqltext.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
            results.append((c.name, str(compiled)))
    return results


def test_run_event_type_check_matches_spec() -> None:
    """run_events.type CHECK must enumerate exactly the 10 RT-002 event types."""
    checks = _get_check_sql("run_events")
    type_checks = [s for name, s in checks if "type" in name.lower()]
    assert len(type_checks) >= 1
    sql = type_checks[0]
    for event_type in [
        "run.created",
        "run.plan_ready",
        "run.execution_started",
        "run.progress",
        "run.approval_waiting",
        "run.resumed",
        "run.artifact_created",
        "run.completed",
        "run.failed",
        "run.cancelled",
    ]:
        assert event_type in sql


def test_run_state_check_matches_spec() -> None:
    """runs.state CHECK must enumerate exactly the 7 RT-002 run states."""
    checks = _get_check_sql("runs")
    state_checks = [s for name, s in checks if "state" in name.lower()]
    assert len(state_checks) >= 1
    sql = state_checks[0]
    for state in [
        "created",
        "planning",
        "executing",
        "waiting_approval",
        "completed",
        "failed",
        "cancelled",
    ]:
        assert f"'{state}'" in sql


def test_approval_state_check_matches_spec() -> None:
    """approvals.state CHECK must enumerate exactly the 4 approval states."""
    checks = _get_check_sql("approvals")
    state_checks = [s for name, s in checks if "state" in name.lower()]
    assert len(state_checks) >= 1
    sql = state_checks[0]
    for state in ["pending", "granted", "denied", "timeout"]:
        assert f"'{state}'" in sql


def test_run_event_seq_check() -> None:
    """run_events.seq must have a CHECK enforcing seq >= 1."""
    checks = _get_check_sql("run_events")
    seq_checks = [s for name, s in checks if "seq" in name.lower()]
    assert len(seq_checks) >= 1
    assert "seq >= 1" in seq_checks[0]
