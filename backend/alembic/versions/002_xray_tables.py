"""Xray integration tables

Revision ID: 002_xray_tables
Revises: 001_initial_schema
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create xray_configs table
    op.create_table(
        'xray_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('instance_type', sa.Enum('cloud', 'server', name='xrayinstancetype'), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=False),
        sa.Column('client_id', sa.String(length=255), nullable=True),
        sa.Column('client_secret', sa.String(length=500), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('api_token', sa.String(length=500), nullable=True),
        sa.Column('jira_project_key', sa.String(length=50), nullable=False),
        sa.Column('auto_sync', sa.Boolean(), default=False),
        sa.Column('auto_export', sa.Boolean(), default=True),
        sa.Column('sync_interval_minutes', sa.Integer(), default=60),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.Enum('pending', 'syncing', 'synced', 'failed', name='xraysyncstatus'), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    op.create_index('ix_xray_configs_id', 'xray_configs', ['id'])
    op.create_index('ix_xray_configs_project_id', 'xray_configs', ['project_id'])

    # Create xray_test_sets table
    op.create_table(
        'xray_test_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('xray_config_id', sa.Integer(), nullable=False),
        sa.Column('xray_issue_key', sa.String(length=50), nullable=False),
        sa.Column('xray_issue_id', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sync_status', sa.Enum('pending', 'syncing', 'synced', 'failed', name='xraysyncstatus', create_type=False), default='pending'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('labels', sa.JSON(), default=[]),
        sa.Column('components', sa.JSON(), default=[]),
        sa.Column('fix_versions', sa.JSON(), default=[]),
        sa.Column('test_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['xray_config_id'], ['xray_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_xray_test_sets_id', 'xray_test_sets', ['id'])
    op.create_index('ix_xray_test_sets_xray_issue_key', 'xray_test_sets', ['xray_issue_key'])

    # Create xray_tests table
    op.create_table(
        'xray_tests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_set_id', sa.Integer(), nullable=False),
        sa.Column('xray_issue_key', sa.String(length=50), nullable=False),
        sa.Column('xray_issue_id', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('test_type', sa.Enum('manual', 'gherkin', name='xraytesttype'), nullable=False),
        sa.Column('manual_steps', sa.JSON(), default=[]),
        sa.Column('gherkin_scenario', sa.Text(), nullable=True),
        sa.Column('preconditions', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('labels', sa.JSON(), default=[]),
        sa.Column('rank', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['test_set_id'], ['xray_test_sets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_xray_tests_id', 'xray_tests', ['id'])
    op.create_index('ix_xray_tests_xray_issue_key', 'xray_tests', ['xray_issue_key'])

    # Create xray_step_results table
    op.create_table(
        'xray_step_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('xray_test_id', sa.Integer(), nullable=False),
        sa.Column('test_run_id', sa.Integer(), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_action', sa.Text(), nullable=True),
        sa.Column('step_expected', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'passed', 'failed', 'skipped', 'blocked', name='xraystepstatus'), default='pending'),
        sa.Column('actual_result', sa.Text(), nullable=True),
        sa.Column('screenshot_path', sa.String(length=500), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('export_status', sa.Enum('pending', 'exporting', 'exported', 'failed', 'skipped', name='xrayexportstatus'), default='pending'),
        sa.Column('xray_execution_id', sa.String(length=100), nullable=True),
        sa.Column('exported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('export_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['xray_test_id'], ['xray_tests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_run_id'], ['test_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_xray_step_results_id', 'xray_step_results', ['id'])
    op.create_index('ix_xray_step_results_test_run_id', 'xray_step_results', ['test_run_id'])


def downgrade() -> None:
    op.drop_index('ix_xray_step_results_test_run_id', table_name='xray_step_results')
    op.drop_index('ix_xray_step_results_id', table_name='xray_step_results')
    op.drop_table('xray_step_results')
    
    op.drop_index('ix_xray_tests_xray_issue_key', table_name='xray_tests')
    op.drop_index('ix_xray_tests_id', table_name='xray_tests')
    op.drop_table('xray_tests')
    
    op.drop_index('ix_xray_test_sets_xray_issue_key', table_name='xray_test_sets')
    op.drop_index('ix_xray_test_sets_id', table_name='xray_test_sets')
    op.drop_table('xray_test_sets')
    
    op.drop_index('ix_xray_configs_project_id', table_name='xray_configs')
    op.drop_index('ix_xray_configs_id', table_name='xray_configs')
    op.drop_table('xray_configs')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS xrayexportstatus")
    op.execute("DROP TYPE IF EXISTS xraystepstatus")
    op.execute("DROP TYPE IF EXISTS xraytesttype")
    op.execute("DROP TYPE IF EXISTS xraysyncstatus")
    op.execute("DROP TYPE IF EXISTS xrayinstancetype")
