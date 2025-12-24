"""Add company applications and indexes

Revision ID: add_company_applications
Revises: add_capacity_is_active
Create Date: 2025-12-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_company_applications'
down_revision: Union[str, None] = 'add_capacity_is_active'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем enum для статуса заявки
    op.execute("CREATE TYPE applicationstatus AS ENUM ('pending', 'approved', 'rejected')")

    # Создаем таблицу заявок
    op.create_table(
        'company_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('company_address', sa.String(), nullable=False),
        sa.Column('company_website', sa.String(), nullable=True),
        sa.Column('work_hours', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='applicationstatus', native_enum=False),
                  nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by_admin_id', sa.Integer(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Создаем индексы для company_applications
    op.create_index('ix_company_applications_id', 'company_applications', ['id'])
    op.create_index('ix_company_applications_user_id', 'company_applications', ['user_id'])
    op.create_index('ix_company_applications_status', 'company_applications', ['status'])

    # Добавляем недостающие индексы для оптимизации запросов
    op.create_index('ix_bookings_tour_id', 'bookings', ['tour_id'])
    op.create_index('ix_bookings_user_id', 'bookings', ['user_id'])
    op.create_index('ix_bookings_date', 'bookings', ['date'])
    op.create_index('ix_bookings_status', 'bookings', ['status'])

    op.create_index('ix_reviews_tour_id', 'reviews', ['tour_id'])
    op.create_index('ix_reviews_company_id', 'reviews', ['company_id'])
    op.create_index('ix_reviews_author_id', 'reviews', ['author_id'])

    op.create_index('ix_tours_company_id', 'tours', ['company_id'])
    op.create_index('ix_tours_is_active', 'tours', ['is_active'])


def downgrade() -> None:
    # Удаляем индексы
    op.drop_index('ix_tours_is_active', table_name='tours')
    op.drop_index('ix_tours_company_id', table_name='tours')

    op.drop_index('ix_reviews_author_id', table_name='reviews')
    op.drop_index('ix_reviews_company_id', table_name='reviews')
    op.drop_index('ix_reviews_tour_id', table_name='reviews')

    op.drop_index('ix_bookings_status', table_name='bookings')
    op.drop_index('ix_bookings_date', table_name='bookings')
    op.drop_index('ix_bookings_user_id', table_name='bookings')
    op.drop_index('ix_bookings_tour_id', table_name='bookings')

    # Удаляем таблицу заявок
    op.drop_index('ix_company_applications_status', table_name='company_applications')
    op.drop_index('ix_company_applications_user_id', table_name='company_applications')
    op.drop_index('ix_company_applications_id', table_name='company_applications')
    op.drop_table('company_applications')

    # Удаляем enum
    op.execute('DROP TYPE applicationstatus')