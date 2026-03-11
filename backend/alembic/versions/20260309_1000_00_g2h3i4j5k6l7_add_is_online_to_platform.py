"""Add is_online boolean to platform table

WHY: Differentiate between online marketplaces (Shopee, Lazada, TikTok)
and offline/physical stores within the platform table. Defaults to True
because existing platforms are all online marketplaces.

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-03-09 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g2h3i4j5k6l7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'platform',
        sa.Column('is_online', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
    )


def downgrade() -> None:
    op.drop_column('platform', 'is_online')
