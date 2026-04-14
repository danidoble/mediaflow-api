"""add progress and expires_at to jobs

Revision ID: a3f8d1c2e4b7
Revises: 2170c891734c
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f8d1c2e4b7'
down_revision: Union[str, None] = '2170c891734c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('progress', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'expires_at')
    op.drop_column('jobs', 'progress')
