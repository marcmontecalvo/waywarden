"""ORM table definition for run_events."""

from __future__ import annotations

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    Index,
    String,
    Table,
    UniqueConstraint,
)

from waywarden.infra.db.metadata import metadata

run_events = Table(
    "run_events",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, nullable=False),
    Column("seq", String, nullable=False),
    Column(
        "type",
        String,
        nullable=False,
    ),
    Column("payload", String),
    Column("timestamp", TIMESTAMP(timezone=True), nullable=False),
    Column("causation", String),
    Column("actor", String),
    UniqueConstraint("run_id", "seq", name="uq_run_events_run_id_seq"),
    Index("ix_run_events_run_id_seq", "run_id", "seq"),
    CheckConstraint(
        "type IN ('run.created', 'run.plan_ready', "
        "'run.execution_started', 'run.progress', "
        "'run.approval_waiting', 'run.resumed', "
        "'run.artifact_created', 'run.completed', "
        "'run.failed', 'run.cancelled')",
        name="ck_run_events_type",
    ),
    CheckConstraint("seq >= 1", name="ck_run_events_seq_positive"),
    comment="RT-002 event log",
)
