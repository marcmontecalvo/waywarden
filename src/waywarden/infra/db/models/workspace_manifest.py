"""ORM table definition for workspace_manifests."""

from __future__ import annotations

from sqlalchemy import Column, String, Table
from sqlalchemy.dialects.postgresql import JSONB

from waywarden.infra.db.metadata import metadata

workspace_manifests = Table(
    "workspace_manifests",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, nullable=False, unique=True),
    Column("body", JSONB, nullable=False),
    comment="RT-001 workspace manifest body (JSONB)",
)
