"""Add MFA/2FA fields to users table.

Revision ID: add_mfa_fields
Revises: 
Create Date: 2026-06-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_mfa_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add MFA-related columns to users table."""
    
    # Add mfa_secret column for TOTP secret
    try:
        op.add_column('users', sa.Column('mfa_secret', sa.String(), nullable=True))
    except Exception as e:
        print(f"Warning: Could not add mfa_secret column: {e}")
    
    # Add mfa_enabled column for MFA status
    try:
        op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    except Exception as e:
        print(f"Warning: Could not add mfa_enabled column: {e}")
    
    # Add mfa_backup_codes column for backup recovery codes
    try:
        op.add_column('users', sa.Column('mfa_backup_codes', sa.Text(), nullable=True))
    except Exception as e:
        print(f"Warning: Could not add mfa_backup_codes column: {e}")
    
    # Add mfa_enabled_at column for timestamp
    try:
        op.add_column('users', sa.Column('mfa_enabled_at', sa.DateTime(timezone=True), nullable=True))
    except Exception as e:
        print(f"Warning: Could not add mfa_enabled_at column: {e}")


def downgrade() -> None:
    """Remove MFA-related columns from users table."""
    
    try:
        op.drop_column('users', 'mfa_enabled_at')
    except Exception as e:
        print(f"Warning: Could not drop mfa_enabled_at column: {e}")
    
    try:
        op.drop_column('users', 'mfa_backup_codes')
    except Exception as e:
        print(f"Warning: Could not drop mfa_backup_codes column: {e}")
    
    try:
        op.drop_column('users', 'mfa_enabled')
    except Exception as e:
        print(f"Warning: Could not drop mfa_enabled column: {e}")
    
    try:
        op.drop_column('users', 'mfa_secret')
    except Exception as e:
        print(f"Warning: Could not drop mfa_secret column: {e}")
