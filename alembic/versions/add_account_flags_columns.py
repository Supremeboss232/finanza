"""Add is_system_account and is_admin_account columns to accounts table.

Revision ID: add_account_flags
Revises: 
Create Date: 2026-04-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_account_flags'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_admin_account column if it doesn't exist
    try:
        op.add_column('accounts', sa.Column('is_admin_account', sa.Boolean(), nullable=False, server_default=sa.false(), comment="If True, not subject to user binding enforcement"))
    except Exception:
        pass  # Column already exists
    
    # Add is_system_account column if it doesn't exist
    try:
        op.add_column('accounts', sa.Column('is_system_account', sa.Boolean(), nullable=False, server_default=sa.false(), comment="If True, only allows admin disbursements"))
    except Exception:
        pass  # Column already exists


def downgrade() -> None:
    # Drop columns if reverting
    try:
        op.drop_column('accounts', 'is_system_account')
    except Exception:
        pass
    
    try:
        op.drop_column('accounts', 'is_admin_account')
    except Exception:
        pass
