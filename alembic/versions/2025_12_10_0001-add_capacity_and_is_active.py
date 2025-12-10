"""Add capacity and is_active to tours, unique constraint on companies

Revision ID: add_capacity_is_active
Revises: initial_migration
Create Date: 2025-12-10 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_capacity_is_active'
down_revision: Union[str, None] = 'initial_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add capacity to tours
    op.add_column('tours', sa.Column('capacity', sa.Integer(), nullable=False, server_default='50'))
    
    # Add is_active to tours
    op.add_column('tours', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Add unique constraint on companies.owner_id
    op.create_unique_constraint('uq_companies_owner_id', 'companies', ['owner_id'])


def downgrade() -> None:
    op.drop_constraint('uq_companies_owner_id', 'companies', type_='unique')
    op.drop_column('tours', 'is_active')
    op.drop_column('tours', 'capacity')
