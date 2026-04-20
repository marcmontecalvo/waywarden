"""ORM table definition for tasks."""

from __future__ import annotations

from sqlalchemy import TIMESTAMP, Column, String, Table

from waywarden.infra.db.metadata import metadata

tasks = Table(
    "tasks",
    metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False),
    Column("title", String, nullable=False),
    Column("objective", String, nullable=False),
    Column("state", String, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False),
    comment="Provider-neutral task records",
)
