"""ORM table definition for approvals."""

from __future__ import annotations

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    String,
    Table,
)

from waywarden.infra.db.metadata import metadata

approvals = Table(
    "approvals",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, nullable=False),
    Column("approval_kind", String, nullable=False),
    Column("requested_capability", String),
    Column("summary", String, nullable=False),
    Column("state", String, nullable=False, server_default="pending"),
    Column("requested_at", TIMESTAMP(timezone=True), nullable=False),
    Column("decided_at", TIMESTAMP(timezone=True)),
    Column("decided_by", String),
    Column("expires_at", TIMESTAMP(timezone=True)),
    CheckConstraint(
        "state IN ('pending', 'granted', 'denied', 'timeout')",
        name="ck_approvals_state",
    ),
    comment="Approval decision artifacts referenced by RT-002 events",
)
