"""ORM table definition for session references."""

from __future__ import annotations

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    String,
    Table,
)

from waywarden.infra.db.metadata import metadata

session_references = Table(
    "session_references",
    metadata,
    Column("run_id", String, nullable=False),
    Column("artifact_id", String, nullable=False),
    Column("session_ref", String, nullable=False),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    CheckConstraint(
        "run_id <> '' AND artifact_id <> '' AND session_ref <> ''",
        name="ck_session_ref_not_empty",
    ),
    comment="Coding-session continuity references (P6-3 #94)",
)
