"""ORM table definition for sessions."""

from __future__ import annotations

from sqlalchemy import TIMESTAMP, Column, String, Table

from waywarden.infra.db.metadata import metadata

sessions = Table(
    "sessions",
    metadata,
    Column("id", String, primary_key=True),
    Column("instance_id", String, nullable=False),
    Column("profile", String, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("closed_at", TIMESTAMP(timezone=True)),
    comment="Provider-neutral session records",
)
