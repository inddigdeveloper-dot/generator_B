"""Add job locks table

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_locks",
        sa.Column("job_name", sa.String(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("job_name"),
    )
    op.execute("INSERT INTO job_locks (job_name) VALUES ('qr_inactive_reminder')")


def downgrade() -> None:
    op.drop_table("job_locks")
