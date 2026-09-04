"""Add sector column to cameras table

Revision ID: 0003_add_camera_sector
Revises: 0002_cv_intelligence_schema
Create Date: 2026-09-04 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0003_add_camera_sector'
down_revision: Union[str, None] = '0002_cv_intelligence_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cameras', sa.Column('sector', sa.String(length=100), nullable=True, server_default='Sector Alpha'))


def downgrade() -> None:
    op.drop_column('cameras', 'sector')
