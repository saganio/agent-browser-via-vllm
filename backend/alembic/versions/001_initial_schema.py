"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True, default=dict),
        sa.Column('max_concurrent_tests', sa.Integer(), nullable=True, default=5),
        sa.Column('max_projects', sa.Integer(), nullable=True, default=50),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations'))
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('oidc_sub', sa.String(255), nullable=True),
        sa.Column('oidc_provider', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'developer', 'viewer', name='role'), nullable=False, default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_users_organization_id_organizations')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_oidc_sub'), 'users', ['oidc_sub'], unique=True)

    # Refresh tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(500), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens'))
    )
    op.create_index(op.f('ix_refresh_tokens_id'), 'refresh_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('vllm_config', sa.JSON(), nullable=True, default=dict),
        sa.Column('browser_config', sa.JSON(), nullable=True, default=dict),
        sa.Column('default_commands', sa.JSON(), nullable=True, default=list),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_projects_organization_id_organizations')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_projects_created_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_projects'))
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_slug'), 'projects', ['slug'], unique=False)

    # Test runs table
    op.create_table(
        'test_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='teststatus'), nullable=False, default='pending'),
        sa.Column('triggered_by', sa.Integer(), nullable=True),
        sa.Column('trigger_type', sa.String(50), nullable=True, default='manual'),
        sa.Column('worker_id', sa.String(100), nullable=True),
        sa.Column('celery_task_id', sa.String(100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_test_runs_project_id_projects')),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], name=op.f('fk_test_runs_triggered_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_test_runs'))
    )
    op.create_index(op.f('ix_test_runs_id'), 'test_runs', ['id'], unique=False)

    # Test results table
    op.create_table(
        'test_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_run_id', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(50), nullable=False),
        sa.Column('tool_name', sa.String(100), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True, default=dict),
        sa.Column('success', sa.Boolean(), nullable=True, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('screenshot_path', sa.String(500), nullable=True),
        sa.Column('video_path', sa.String(500), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['test_run_id'], ['test_runs.id'], name=op.f('fk_test_results_test_run_id_test_runs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_test_results'))
    )
    op.create_index(op.f('ix_test_results_id'), 'test_results', ['id'], unique=False)

    # Schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('cron_expression', sa.String(100), nullable=False),
        sa.Column('timezone', sa.String(50), nullable=True, default='UTC'),
        sa.Column('enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='teststatus'), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_schedules_project_id_projects')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_schedules'))
    )
    op.create_index(op.f('ix_schedules_id'), 'schedules', ['id'], unique=False)

    # Notification channels table
    op.create_table(
        'notification_channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('channel_type', sa.Enum('email', 'slack', 'webhook', 'discord', name='channeltype'), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True, default=dict),
        sa.Column('notify_on', sa.JSON(), nullable=True, default=list),
        sa.Column('enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_notification_channels_organization_id_organizations')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_channels'))
    )
    op.create_index(op.f('ix_notification_channels_id'), 'notification_channels', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notification_channels_id'), table_name='notification_channels')
    op.drop_table('notification_channels')
    op.drop_index(op.f('ix_schedules_id'), table_name='schedules')
    op.drop_table('schedules')
    op.drop_index(op.f('ix_test_results_id'), table_name='test_results')
    op.drop_table('test_results')
    op.drop_index(op.f('ix_test_runs_id'), table_name='test_runs')
    op.drop_table('test_runs')
    op.drop_index(op.f('ix_projects_slug'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(op.f('ix_users_oidc_sub'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_id'), table_name='organizations')
    op.drop_table('organizations')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS role")
    op.execute("DROP TYPE IF EXISTS teststatus")
    op.execute("DROP TYPE IF EXISTS channeltype")
