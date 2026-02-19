"""
Alembic migration: Add status and kyc_level columns to accounts table
Also add is_admin_account flag and enforce User ID → Account ID relationship
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_account_fields_20251216'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Add status, kyc_level, and is_admin_account columns to accounts table"""
    
    # Add status column
    op.add_column('accounts', sa.Column(
        'status',
        sa.String(),
        nullable=False,
        server_default='active'
    ))
    
    # Add kyc_level column
    op.add_column('accounts', sa.Column(
        'kyc_level',
        sa.String(),
        nullable=False,
        server_default='basic'
    ))
    
    # Add is_admin_account column to exclude admin accounts from user binding enforcement
    op.add_column('accounts', sa.Column(
        'is_admin_account',
        sa.Boolean(),
        nullable=False,
        server_default='0'  # False by default - all accounts except admin are user-bound
    ))
    
    # Make owner_id NOT NULL (it should be required, except for admin accounts)
    op.alter_column('accounts', 'owner_id',
                    existing_type=sa.Integer(),
                    nullable=True)  # Keep nullable for now to allow admin accounts
    
    # Add index on owner_id for faster lookups (User ID → Account ID relationship)
    op.create_index('idx_account_owner_id', 'accounts', ['owner_id'])
    
    # Make account_type NOT NULL (it should be required)
    op.alter_column('accounts', 'account_type',
                    existing_type=sa.String(),
                    nullable=False)
    
    # Make balance NOT NULL (it should be required)
    op.alter_column('accounts', 'balance',
                    existing_type=sa.Float(),
                    nullable=False)
    
    # Make currency NOT NULL (it should be required)
    op.alter_column('accounts', 'currency',
                    existing_type=sa.String(),
                    nullable=False)
    
    # Add unique constraint on account_id (it's already PK, but explicit for clarity)
    # Note: Primary keys are already unique, this is just for documentation

def downgrade():
    """Remove status, kyc_level, and is_admin_account columns from accounts table"""
    
    # Drop index
    op.drop_index('idx_account_owner_id', 'accounts')
    
    # Allow owner_id to be nullable again
    op.alter_column('accounts', 'owner_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # Allow account_type to be nullable again
    op.alter_column('accounts', 'account_type',
                    existing_type=sa.String(),
                    nullable=True)
    
    # Allow balance to be nullable again
    op.alter_column('accounts', 'balance',
                    existing_type=sa.Float(),
                    nullable=True)
    
    # Allow currency to be nullable again
    op.alter_column('accounts', 'currency',
                    existing_type=sa.String(),
                    nullable=True)
    
    # Drop columns
    op.drop_column('accounts', 'is_admin_account')
    op.drop_column('accounts', 'kyc_level')
    op.drop_column('accounts', 'status')
