"""initial"""

import sqlalchemy as sa

from alembic import op

revision = "20260413_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("sessions")
