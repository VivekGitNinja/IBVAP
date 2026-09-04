"""Initial core database schema with performance indexes

Revision ID: 0001_initial_core_schema
Revises: 
Create Date: 2026-09-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial_core_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('full_name', sa.String(length=120), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    # 2. Cameras
    op.create_table(
        'cameras',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('stream_url', sa.String(length=500), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('bop', sa.String(length=120), nullable=False),
        sa.Column('camera_type', sa.String(length=40), nullable=False),
        sa.Column('fps', sa.Integer(), nullable=False),
        sa.Column('resolution', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('health_score', sa.Float(), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('analytics_enabled', sa.Boolean(), nullable=False),
        sa.Column('detection_interval', sa.Integer(), nullable=False),
        sa.Column('max_inference_fps', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cameras_name', 'cameras', ['name'])
    op.create_index('ix_cameras_status', 'cameras', ['status'])
    op.create_index('ix_cameras_bop_status', 'cameras', ['bop', 'status'])

    # 3. Incidents
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_code', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('threat_score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('reason_codes', sa.JSON(), nullable=False),
        sa.Column('event_ids', sa.JSON(), nullable=False),
        sa.Column('detection_ids', sa.JSON(), nullable=False),
        sa.Column('track_ids', sa.JSON(), nullable=False),
        sa.Column('camera_id', sa.Integer(), nullable=True),
        sa.Column('camera_name', sa.String(length=120), nullable=False),
        sa.Column('zone_name', sa.String(length=100), nullable=False),
        sa.Column('fingerprint', sa.String(length=128), nullable=False),
        sa.Column('correlated_ids', sa.JSON(), nullable=False),
        sa.Column('recommended_action', sa.String(length=300), nullable=False),
        sa.Column('ai_assessment', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=80), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('closed_by', sa.String(length=80), nullable=True),
        sa.Column('escalated_at', sa.DateTime(), nullable=True),
        sa.Column('escalated_by', sa.String(length=80), nullable=True),
        sa.Column('timeline', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('incident_code')
    )
    op.create_index('ix_incidents_created_at', 'incidents', ['created_at'])
    op.create_index('ix_incidents_threat_score', 'incidents', ['threat_score'])
    op.create_index('ix_incidents_status_severity', 'incidents', ['status', 'severity'])
    op.create_index('ix_incidents_camera_created', 'incidents', ['camera_id', 'created_at'])

    # 4. Evidence
    op.create_table(
        'evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('evidence_type', sa.String(length=30), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('manifest_path', sa.String(length=500), nullable=False),
        sa.Column('manifest_data', sa.JSON(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('threat_score', sa.Float(), nullable=False),
        sa.Column('camera_id', sa.Integer(), nullable=True),
        sa.Column('camera_name', sa.String(length=120), nullable=False),
        sa.Column('detection_metadata', sa.JSON(), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_incident_id', 'evidence', ['incident_id'])
    op.create_index('ix_evidence_sha256', 'evidence', ['sha256'])
    op.create_index('ix_evidence_incident_type', 'evidence', ['incident_id', 'evidence_type'])

    # 5. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor', sa.String(length=80), nullable=False),
        sa.Column('actor_role', sa.String(length=30), nullable=False),
        sa.Column('action', sa.String(length=120), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=80), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=False),
        sa.Column('entry_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_actor', 'audit_logs', ['actor'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_actor_created', 'audit_logs', ['actor', 'created_at'])
    op.create_index('ix_audit_logs_target', 'audit_logs', ['target_type', 'target_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('evidence')
    op.drop_table('incidents')
    op.drop_table('cameras')
    op.drop_table('users')
