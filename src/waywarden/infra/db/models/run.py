"""ORM table definition for runs."""

from __future__ import annotations

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    String,
    Table,
)

from waywarden.infra.db.metadata import metadata

runs = Table(
    "runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("instance_id", String, nullable=False),
    Column("task_id", String),
    Column("profile", String, nullable=False),
    Column(
        "policy_preset",
        String,
        nullable=False,
    ),
    Column("manifest_ref", String, nullable=False),
    Column("entrypoint", String, nullable=False),
    Column("state", String, nullable=False, server_default="created"),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False),
    Column("terminal_seq", String),
    CheckConstraint(
        "policy_preset IN ('yolo', 'ask', 'allowlist', 'custom')",
        name="ck_runs_policy_preset",
    ),
    CheckConstraint(
        "state IN ('created', 'planning', 'executing', "
        "'waiting_approval', 'completed', 'failed', 'cancelled')",
        name="ck_runs_state",
    ),
    comment="RT-002 run records",
)
