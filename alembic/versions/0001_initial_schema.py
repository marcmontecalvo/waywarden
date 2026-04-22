"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-20 14:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True)),
        comment="Provider-neutral session records",
    )

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("objective", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        comment="Provider-neutral task records",
    )

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB()),
        comment="Provider-neutral message records",
    )

    # --- runs ---
    op.create_table(
        "runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String()),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column("policy_preset", sa.String(), nullable=False),
        sa.Column("manifest_ref", sa.String(), nullable=False),
        sa.Column("entrypoint", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="created"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("terminal_seq", sa.String()),
        sa.CheckConstraint(
            "policy_preset IN ('yolo', 'ask', 'allowlist', 'custom')",
            name="ck_runs_policy_preset",
        ),
        sa.CheckConstraint(
            "state IN ('created', 'planning', 'executing', "
            "'waiting_approval', 'completed', 'failed', 'cancelled')",
            name="ck_runs_state",
        ),
        comment="RT-002 run records",
    )

    # --- run_events ---
    op.create_table(
        "run_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("seq", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("payload", sa.String()),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("causation", sa.String()),
        sa.Column("actor", sa.String()),
        sa.UniqueConstraint("run_id", "seq", name="uq_run_events_run_id_seq"),
        sa.CheckConstraint(
            "type IN ('run.created', 'run.plan_ready', "
            "'run.execution_started', 'run.progress', "
            "'run.approval_waiting', 'run.resumed', "
            "'run.artifact_created', 'run.completed', "
            "'run.failed', 'run.cancelled')",
            name="ck_run_events_type",
        ),
        sa.CheckConstraint("CAST(seq AS INTEGER) >= 1", name="ck_run_events_seq_positive"),
        comment="RT-002 event log",
    )
    op.create_index("ix_run_events_run_id_seq", "run_events", ["run_id", "seq"])

    # --- approvals ---
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("approval_kind", sa.String(), nullable=False),
        sa.Column("requested_capability", sa.String()),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "requested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("decided_by", sa.String()),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.CheckConstraint(
            "state IN ('pending', 'granted', 'denied', 'timeout')",
            name="ck_approvals_state",
        ),
        comment="Approval decision artifacts referenced by RT-002 events",
    )

    # --- workspace_manifests ---
    op.create_table(
        "workspace_manifests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), nullable=False, unique=True),
        sa.Column("body", postgresql.JSONB(), nullable=False),
        comment="RT-001 workspace manifest body (JSONB)",
    )

    # --- checkpoints ---
    op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("label", sa.String()),
        comment="RT-002 checkpoint records",
    )

    # --- token_usage ---
    op.create_table(
        "token_usage",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.String(),
            nullable=False,
        ),
        sa.Column("call_ref", sa.String()),
        sa.UniqueConstraint("run_id", "seq", name="uq_token_usage_run_id_seq"),
        sa.CheckConstraint("seq >= 1", name="ck_token_usage_seq_positive"),
        sa.CheckConstraint(
            "total_tokens = prompt_tokens + completion_tokens",
            name="ck_token_usage_total_eq_sum",
        ),
        sa.CheckConstraint(
            "prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0",
            name="ck_token_usage_non_negative",
        ),
        comment="Token usage accounting (persisted outside RT-002 event log)",
    )


def downgrade() -> None:
    op.drop_table("token_usage")
    op.drop_table("checkpoints")
    op.drop_table("workspace_manifests")
    op.drop_table("approvals")
    op.drop_table("run_events")
    op.drop_table("runs")
    op.drop_table("messages")
    op.drop_table("tasks")
    op.drop_table("sessions")
