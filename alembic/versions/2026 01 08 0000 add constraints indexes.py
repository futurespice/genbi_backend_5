"""Add unique constraints and performance indexes

Revision ID: add_constraints_indexes
Revises: add_coordinates_to_tours
Create Date: 2026-01-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_constraints_indexes'
down_revision: Union[str, None] = 'add_coordinates_to_tours'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================
    # ✅ PARTIAL UNIQUE INDEXES - Защита от дублирования
    # ============================================
    # ВАЖНО: В PostgreSQL используем create_index с unique=True для partial indexes

    # 1. Нельзя иметь несколько активных бронирований на один тур в одну дату
    op.create_index(
        'uq_bookings_user_tour_date_active',
        'bookings',
        ['user_id', 'tour_id', 'date'],
        unique=True,
        postgresql_where=sa.text("status != 'cancelled'")
    )

    # 2. Один отзыв на один тур от пользователя
    op.create_index(
        'uq_reviews_author_tour',
        'reviews',
        ['author_id', 'tour_id'],
        unique=True,
        postgresql_where=sa.text("tour_id IS NOT NULL")
    )

    # 3. Один отзыв на одну компанию от пользователя
    op.create_index(
        'uq_reviews_author_company',
        'reviews',
        ['author_id', 'company_id'],
        unique=True,
        postgresql_where=sa.text("company_id IS NOT NULL")
    )

    # 4. Одна заявка в статусе pending от пользователя
    op.create_index(
        'uq_applications_user_pending',
        'company_applications',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text("status = 'pending'")
    )

    # ============================================
    # ✅ PERFORMANCE INDEXES - Оптимизация запросов
    # ============================================

    # Composite indexes для частых запросов

    # 1. Бронирования: фильтр по туру + дате + статусу
    op.create_index(
        'ix_bookings_tour_date_status',
        'bookings',
        ['tour_id', 'date', 'status']
    )

    # 2. Туры: активные туры компании (для списков)
    op.create_index(
        'ix_tours_company_active',
        'tours',
        ['company_id', 'is_active']
    )

    # 3. Туры: поиск по локации + активность
    op.create_index(
        'ix_tours_location_active',
        'tours',
        ['location', 'is_active']
    )

    # 4. Отзывы: для расчета рейтинга тура
    op.create_index(
        'ix_reviews_tour_rating',
        'reviews',
        ['tour_id', 'rating']
    )

    # 5. Заявки: фильтр по статусу для админки
    op.create_index(
        'ix_applications_status_created',
        'company_applications',
        ['status', 'created_at']
    )


def downgrade() -> None:
    # Удаляем индексы
    op.drop_index('ix_applications_status_created', table_name='company_applications')
    op.drop_index('ix_reviews_tour_rating', table_name='reviews')
    op.drop_index('ix_tours_location_active', table_name='tours')
    op.drop_index('ix_tours_company_active', table_name='tours')
    op.drop_index('ix_bookings_tour_date_status', table_name='bookings')

    # Удаляем unique partial indexes
    op.drop_index('uq_applications_user_pending', table_name='company_applications')
    op.drop_index('uq_reviews_author_company', table_name='reviews')
    op.drop_index('uq_reviews_author_tour', table_name='reviews')
    op.drop_index('uq_bookings_user_tour_date_active', table_name='bookings')