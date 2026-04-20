"""ORM table definition for messages."""

from __future__ import annotations

from sqlalchemy import JSON, TIMESTAMP, Column, String, Table

from waywarden.infra.db.metadata import metadata

messages = Table(
    "messages",
    metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False),
    Column("role", String, nullable=False),
    Column("content", String, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("metadata", JSON),
    comment="Provider-neutral message records",
)
