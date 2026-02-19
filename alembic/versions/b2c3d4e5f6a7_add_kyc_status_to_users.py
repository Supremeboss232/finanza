"""add_kyc_status_to_users

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-16 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add kyc_status column to users table"""
    # Add kyc_status column with default value 'not_started'
    # This allows existing users to continue without KYC initially
    op.add_column(
        'user',
        sa.Column(
            'kyc_status',
            sa.String(20),
            nullable=False,
            server_default='not_started'
        )
    )
    
    # Create an index on kyc_status for efficient filtering
    op.create_index(
        'idx_user_kyc_status',
        'user',
        ['kyc_status']
    )


def downgrade() -> None:
    """Revert kyc_status column from users table"""
    op.drop_index('idx_user_kyc_status', table_name='user')
    op.drop_column('user', 'kyc_status')
