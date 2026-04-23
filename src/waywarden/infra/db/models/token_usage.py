"""ORM table definition for token_usage.

Schema: id, run_id, seq, provider, model, prompt_tokens, completion_tokens,
        total_tokens, recorded_at, call_ref.
"""

from __future__ import annotations

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
)

from waywarden.infra.db.metadata import metadata

token_usage = Table(
    "token_usage",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, nullable=False),
    Column("seq", Integer, nullable=False),
    Column("provider", String, nullable=False),
    Column("model", String, nullable=False),
    Column("prompt_tokens", Integer, nullable=False),
    Column("completion_tokens", Integer, nullable=False),
    Column("total_tokens", Integer, nullable=False),
    Column("recorded_at", TIMESTAMP(timezone=True), nullable=False),
    Column("call_ref", String, nullable=True),
    UniqueConstraint("run_id", "seq", name="uq_token_usage_run_id_seq"),
    Index("ix_token_usage_run_id_seq", "run_id", "seq"),
    CheckConstraint("seq >= 1", name="ck_token_usage_seq_positive"),
    CheckConstraint(
        "total_tokens = prompt_tokens + completion_tokens",
        name="ck_token_usage_total_eq_sum",
    ),
    CheckConstraint(
        "prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0",
        name="ck_token_usage_non_negative",
    ),
    comment="Token usage accounting (persisted outside RT-002 event log)",
)
