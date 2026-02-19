"""Priority 3 - Database migration for scheduled transfers, webhooks, mobile deposits, and compliance features.

Revision ID: 001_priority_3_base
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_priority_3_base'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scheduled_transfers table
    op.create_table(
        'scheduled_transfers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('from_account_id', sa.Integer(), nullable=False),
        sa.Column('to_account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('frequency', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['from_account_id'], ['account.id'], ),
        sa.ForeignKeyConstraint(['to_account_id'], ['account.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_scheduled_transfers_user_id', 'user_id'),
        sa.Index('ix_scheduled_transfers_status', 'status'),
    )

    # Create scheduled_transfer_executions table
    op.create_table(
        'scheduled_transfer_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scheduled_transfer_id', sa.Integer(), nullable=False),
        sa.Column('execution_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['scheduled_transfer_id'], ['scheduled_transfers.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transaction.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_scheduled_transfer_executions_scheduled_transfer_id', 'scheduled_transfer_id'),
        sa.Index('ix_scheduled_transfer_executions_status', 'status'),
    )

    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('secret_key', sa.String(length=255), nullable=True),
        sa.Column('events', sa.Text(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_webhooks_user_id', 'user_id'),
        sa.Index('ix_webhooks_active', 'active'),
    )

    # Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_attempt', sa.DateTime(), nullable=True),
        sa.Column('next_retry', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_webhook_deliveries_webhook_id', 'webhook_id'),
        sa.Index('ix_webhook_deliveries_status', 'status'),
        sa.Index('ix_webhook_deliveries_created_at', 'created_at'),
    )

    # Create mobile_deposits table
    op.create_table(
        'mobile_deposits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('front_image_url', sa.String(length=2048), nullable=True),
        sa.Column('back_image_url', sa.String(length=2048), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('quality_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('check_detected', sa.Boolean(), nullable=True),
        sa.Column('endorsement_found', sa.Boolean(), nullable=True),
        sa.Column('image_quality_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_mobile_deposits_user_id', 'user_id'),
        sa.Index('ix_mobile_deposits_status', 'status'),
        sa.Index('ix_mobile_deposits_created_at', 'created_at'),
    )

    # Create flagged_transactions table
    op.create_table(
        'flagged_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('flag_reason', sa.String(length=255), nullable=False),
        sa.Column('risk_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('investigation_notes', sa.Text(), nullable=True),
        sa.Column('resolution_date', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['resolved_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transaction.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_flagged_transactions_user_id', 'user_id'),
        sa.Index('ix_flagged_transactions_status', 'status'),
    )

    # Create country_risk_assessment table
    op.create_table(
        'country_risk_assessment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('country_code', sa.String(length=2), nullable=False),
        sa.Column('country_name', sa.String(length=255), nullable=False),
        sa.Column('risk_rating', sa.String(length=50), nullable=False),
        sa.Column('aml_risk', sa.String(length=50), nullable=True),
        sa.Column('cft_risk', sa.String(length=50), nullable=True),
        sa.Column('transaction_limit', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_country_risk_country_code', 'country_code'),
        sa.UniqueConstraint('country_code'),
    )

    # Create sanctions_screening table
    op.create_table(
        'sanctions_screening',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('screening_date', sa.DateTime(), nullable=False),
        sa.Column('database', sa.String(length=50), nullable=False),
        sa.Column('match_found', sa.Boolean(), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_sanctions_screening_name', 'name'),
        sa.Index('ix_sanctions_screening_screening_date', 'screening_date'),
    )


def downgrade() -> None:
    op.drop_table('sanctions_screening')
    op.drop_table('country_risk_assessment')
    op.drop_table('flagged_transactions')
    op.drop_table('mobile_deposits')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
    op.drop_table('scheduled_transfer_executions')
    op.drop_table('scheduled_transfers')
