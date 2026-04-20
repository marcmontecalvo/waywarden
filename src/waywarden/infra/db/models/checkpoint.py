"""ORM table definition for checkpoints."""

from __future__ import annotations

from sqlalchemy import TIMESTAMP, Column, String, Table

from waywarden.infra.db.metadata import metadata

checkpoints = Table(
    "checkpoints",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("label", String),
    comment="RT-002 checkpoint records",
)
