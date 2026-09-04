"""CV and Intelligence Extension Schema (Zones, PlateReads, Watchlist, Indexes)

Revision ID: 0002_cv_intelligence_schema
Revises: 0001_initial_core_schema
Create Date: 2026-09-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0002_cv_intelligence_schema'
down_revision: Union[str, None] = '0001_initial_core_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Plate Reads
    op.create_table(
        'plate_reads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('detection_id', sa.Integer(), nullable=True),
        sa.Column('camera_id', sa.Integer(), nullable=True),
        sa.Column('plate_text', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('frame_index', sa.Integer(), nullable=False),
        sa.Column('timestamp_ms', sa.Float(), nullable=False),
        sa.Column('bbox', sa.JSON(), nullable=False),
        sa.Column('method', sa.String(length=40), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_plate_reads_plate_text', 'plate_reads', ['plate_text'])
    op.create_index('ix_plate_reads_job_id', 'plate_reads', ['job_id'])
    op.create_index('ix_plate_reads_detection_id', 'plate_reads', ['detection_id'])

    # 2. Watchlist
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('face_image_path', sa.String(length=500), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(length=80), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_watchlist_name', 'watchlist', ['name'])

    # 3. Performance Indexes on existing tables
    op.create_index('ix_detections_job_id', 'detections', ['job_id'])
    op.create_index('ix_detections_track_id', 'detections', ['track_id'])
    op.create_index('ix_incidents_job_id', 'incidents', ['job_id'])


def downgrade() -> None:
    op.drop_table('watchlist')
    op.drop_table('plate_reads')
