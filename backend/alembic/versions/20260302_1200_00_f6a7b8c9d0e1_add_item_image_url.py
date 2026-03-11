"""Add image_url column to items table

Adds an optional image_url column (VARCHAR 500) to store the path/URL
of the main product image uploaded via the item form.

Revision ID: f6a7b8c9d0e1
Revises: e6f7a8b9c0d1
Create Date: 2026-03-02 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("image_url", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("items", "image_url")
