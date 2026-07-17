"""Add MFA fields to users table

Revision ID: add_mfa_fields_blocking_task
Revises: 001_priority_3_base
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_mfa_fields_blocking_task'
down_revision = 'add_account_flags_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add MFA fields to users table
    op.add_column('users', sa.Column('mfa_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), server_default=sa.literal(False), nullable=False))
    op.add_column('users', sa.Column('mfa_backup_codes', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('mfa_enabled_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove MFA fields from users table
    op.drop_column('users', 'mfa_enabled_at')
    op.drop_column('users', 'mfa_backup_codes')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'mfa_secret')
