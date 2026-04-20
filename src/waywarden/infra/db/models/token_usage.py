"""ORM table definition for token_usage (scaffold — P2-11 / #46 fills behavior)."""

from __future__ import annotations

from sqlalchemy import TIMESTAMP, Column, String, Table

from waywarden.infra.db.metadata import metadata

token_usage = Table(
    "token_usage",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, nullable=False),
    Column("model", String, nullable=False),
    Column("direction", String, nullable=False),
    Column("kind", String),
    Column("count", String),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    comment="Token usage accounting (scaffold)",
)
