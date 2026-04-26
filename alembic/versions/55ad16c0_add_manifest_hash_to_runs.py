"""add_manifest_hash_to_runs

Revision ID: 55ad16c0
Revises: c4614d08b9a7
Create Date: 2026-04-25 14:00:00.000000

Adds the manifest_hash column to the runs table to support
ResumeService manifest-drift detection (P4-7 / #70).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "55ad16c0"
down_revision: str | None = "c4614d08b9a7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE runs ADD COLUMN manifest_hash VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE runs DROP COLUMN manifest_hash")
