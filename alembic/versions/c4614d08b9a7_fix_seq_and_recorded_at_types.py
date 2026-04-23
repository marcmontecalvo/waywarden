"""fix_seq_and_recorded_at_types

Revision ID: c4614d08b9a7
Revises: 0001
Create Date: 2026-04-22 21:33:52.690494+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4614d08b9a7"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Fix run_events.seq: was String, should be INTEGER per RT-002 spec
    # Use USING clause to handle existing string data (e.g. "1" -> 1)
    op.execute("ALTER TABLE run_events ALTER COLUMN seq TYPE INTEGER USING seq::integer")

    # Fix run_events.payload: was String, should be JSONB per P2-7 spec
    # Use USING to parse existing text as JSON
    op.execute("ALTER TABLE run_events ALTER COLUMN payload TYPE JSONB USING payload::jsonb")

    # Fix token_usage.recorded_at: was String, should be TIMESTAMPTZ per spec
    op.execute(
        "ALTER TABLE token_usage ALTER COLUMN recorded_at TYPE TIMESTAMPTZ "
        "USING recorded_at::timestamptz"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE token_usage ALTER COLUMN recorded_at TYPE VARCHAR USING recorded_at::varchar"
    )
    op.execute("ALTER TABLE run_events ALTER COLUMN payload TYPE VARCHAR USING payload::varchar")
    op.execute("ALTER TABLE run_events ALTER COLUMN seq TYPE VARCHAR USING seq::varchar")
