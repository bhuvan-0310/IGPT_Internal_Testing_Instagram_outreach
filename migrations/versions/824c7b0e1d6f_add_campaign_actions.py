"""add campaign action plans

Revision ID: 824c7b0e1d6f
Revises: 657b159683cc
Create Date: 2026-10-25 16:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "824c7b0e1d6f"
down_revision: Union[str, Sequence[str], None] = "657b159683cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "campaign_actions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"message\"]'"),
        ),
    )
    op.alter_column("campaigns", "campaign_actions", server_default=None)


def downgrade() -> None:
    op.drop_column("campaigns", "campaign_actions")
