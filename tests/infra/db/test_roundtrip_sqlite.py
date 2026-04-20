"""Round-trip test: persist and reload a Run via the ORM layer (SQLite)."""

from datetime import UTC, datetime

from sqlalchemy import MetaData, create_engine, select

from waywarden.domain.ids import InstanceId, RunId, TaskId
from waywarden.domain.run import Run
from waywarden.infra.db.models.run import runs


def test_run_roundtrips() -> None:
    """A Run domain instance persists and reloads equal via the mapped ORM."""
    # Create the domain instance before any ORM instrumentation
    now = datetime.now(UTC)
    run = Run(
        id=RunId("run_001"),
        instance_id=InstanceId("inst_001"),
        task_id=TaskId("task_001"),
        profile="test",
        policy_preset="ask",
        manifest_ref="manifest://runs/run_001/v1",
        entrypoint="cli",
        state="created",
        created_at=now,
        updated_at=now,
        terminal_seq=None,
    )

    # Use a local metadata to avoid JSONB (workspace_manifests) on SQLite
    local_meta = MetaData()
    runs.to_metadata(local_meta)

    engine = create_engine("sqlite:///:memory:")
    local_meta.create_all(engine)

    # Persist via the table (frozen dataclasses with slots cannot be
    # instrumented by SQLAlchemy ORM, so we use the table directly)
    with engine.connect() as conn:
        conn.execute(
            runs.insert().values(
                id=run.id,
                instance_id=run.instance_id,
                task_id=run.task_id,
                profile=run.profile,
                policy_preset=run.policy_preset,
                manifest_ref=run.manifest_ref,
                entrypoint=run.entrypoint,
                state=run.state,
                created_at=run.created_at,
                updated_at=run.updated_at,
                terminal_seq=run.terminal_seq,
            )
        )
        conn.commit()

    # Reload and verify
    with engine.connect() as conn:
        row = conn.execute(
            select(
                runs.c.id,
                runs.c.instance_id,
                runs.c.task_id,
                runs.c.profile,
                runs.c.policy_preset,
                runs.c.manifest_ref,
                runs.c.entrypoint,
                runs.c.state,
                runs.c.created_at,
                runs.c.updated_at,
                runs.c.terminal_seq,
            ).where(runs.c.id == "run_001")
        ).first()
        assert row is not None
        assert row.id == run.id
        assert row.instance_id == run.instance_id
        assert row.task_id == run.task_id
        assert row.profile == run.profile
        assert row.policy_preset == run.policy_preset
        assert row.manifest_ref == run.manifest_ref
        assert row.entrypoint == run.entrypoint
        assert row.state == run.state
        # SQLite may strip tzinfo on round-trip; compare naive versions
        ca = row.created_at.replace(tzinfo=None) if row.created_at.tzinfo else row.created_at
        ua = row.updated_at.replace(tzinfo=None) if row.updated_at.tzinfo else row.updated_at
        assert ca == run.created_at.replace(tzinfo=None)
        assert ua == run.updated_at.replace(tzinfo=None)
        assert row.terminal_seq == run.terminal_seq
