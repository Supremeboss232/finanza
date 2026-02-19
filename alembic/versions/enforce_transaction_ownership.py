"""enforce_transaction_ownership

Revision ID: enforce_tx_ownership_001
Revises: (latest)
Create Date: 2025-12-16 12:00:00.000000

This migration enforces transaction ownership:
1. Removes all orphaned transactions (user_id is NULL)
2. Requires user_id and account_id on all transactions going forward
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'enforce_tx_ownership_001'
down_revision = None  # Set this to the latest revision ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Delete orphaned transactions (those with NULL user_id)
    op.execute(
        """
        DELETE FROM transactions 
        WHERE user_id IS NULL 
        OR account_id IS NULL;
        """
    )
    
    # Step 2: Make user_id NOT NULL
    op.alter_column(
        'transactions',
        'user_id',
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True
    )
    
    # Step 3: Make account_id NOT NULL
    op.alter_column(
        'transactions',
        'account_id',
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True
    )


def downgrade() -> None:
    # Revert NOT NULL constraints for rollback
    op.alter_column(
        'transactions',
        'account_id',
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False
    )
    
    op.alter_column(
        'transactions',
        'user_id',
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False
    )
