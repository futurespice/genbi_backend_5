"""Add cascade delete to foreign keys

Revision ID: add_cascade_delete
Revises: add_constraints_indexes
Create Date: 2026-01-08 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_cascade_delete'
down_revision: Union[str, None] = 'add_constraints_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    ✅ КРИТИЧНО: Добавляем каскадное удаление для всех foreign keys

    При удалении:
    - User → Company (SET NULL) - компания остается, но без владельца
    - Company → Tours (CASCADE) - удаляются все туры компании
    - Tour → Bookings (CASCADE) - удаляются все бронирования тура
    - Tour → Reviews (CASCADE) - удаляются все отзывы на тур
    - User → Bookings (SET NULL) - бронирования остаются, но user_id = NULL
    - User → Reviews (SET NULL) - отзывы остаются, но author_id = NULL
    """

    # ============================================
    # Companies
    # ============================================

    # 1. Company.owner_id → User (SET NULL)
    op.drop_constraint('companies_owner_id_fkey', 'companies', type_='foreignkey')
    op.create_foreign_key(
        'companies_owner_id_fkey',
        'companies', 'users',
        ['owner_id'], ['id'],
        ondelete='SET NULL'
    )

    # ============================================
    # Tours
    # ============================================

    # 2. Tour.company_id → Company (CASCADE)
    op.drop_constraint('tours_company_id_fkey', 'tours', type_='foreignkey')
    op.create_foreign_key(
        'tours_company_id_fkey',
        'tours', 'companies',
        ['company_id'], ['id'],
        ondelete='CASCADE'
    )

    # ============================================
    # Bookings
    # ============================================

    # 3. Booking.tour_id → Tour (CASCADE)
    op.drop_constraint('bookings_tour_id_fkey', 'bookings', type_='foreignkey')
    op.create_foreign_key(
        'bookings_tour_id_fkey',
        'bookings', 'tours',
        ['tour_id'], ['id'],
        ondelete='CASCADE'
    )

    # 4. Booking.user_id → User (SET NULL)
    op.drop_constraint('bookings_user_id_fkey', 'bookings', type_='foreignkey')
    op.create_foreign_key(
        'bookings_user_id_fkey',
        'bookings', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )

    # ============================================
    # Reviews
    # ============================================

    # 5. Review.tour_id → Tour (CASCADE)
    op.drop_constraint('reviews_tour_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key(
        'reviews_tour_id_fkey',
        'reviews', 'tours',
        ['tour_id'], ['id'],
        ondelete='CASCADE'
    )

    # 6. Review.company_id → Company (CASCADE)
    op.drop_constraint('reviews_company_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key(
        'reviews_company_id_fkey',
        'reviews', 'companies',
        ['company_id'], ['id'],
        ondelete='CASCADE'
    )

    # 7. Review.author_id → User (SET NULL)
    op.drop_constraint('reviews_author_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key(
        'reviews_author_id_fkey',
        'reviews', 'users',
        ['author_id'], ['id'],
        ondelete='SET NULL'
    )

    # ============================================
    # Company Applications
    # ============================================

    # 8. CompanyApplication.user_id → User (CASCADE)
    op.drop_constraint('company_applications_user_id_fkey', 'company_applications', type_='foreignkey')
    op.create_foreign_key(
        'company_applications_user_id_fkey',
        'company_applications', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # 9. CompanyApplication.reviewed_by_admin_id → User (SET NULL)
    op.drop_constraint('company_applications_reviewed_by_admin_id_fkey', 'company_applications', type_='foreignkey')
    op.create_foreign_key(
        'company_applications_reviewed_by_admin_id_fkey',
        'company_applications', 'users',
        ['reviewed_by_admin_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Откат к обычным foreign keys без cascade"""

    # Откатываем все к простым foreign keys (no action)

    # Company Applications
    op.drop_constraint('company_applications_reviewed_by_admin_id_fkey', 'company_applications', type_='foreignkey')
    op.create_foreign_key('company_applications_reviewed_by_admin_id_fkey', 'company_applications', 'users',
                          ['reviewed_by_admin_id'], ['id'])

    op.drop_constraint('company_applications_user_id_fkey', 'company_applications', type_='foreignkey')
    op.create_foreign_key('company_applications_user_id_fkey', 'company_applications', 'users', ['user_id'], ['id'])

    # Reviews
    op.drop_constraint('reviews_author_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_author_id_fkey', 'reviews', 'users', ['author_id'], ['id'])

    op.drop_constraint('reviews_company_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_company_id_fkey', 'reviews', 'companies', ['company_id'], ['id'])

    op.drop_constraint('reviews_tour_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_tour_id_fkey', 'reviews', 'tours', ['tour_id'], ['id'])

    # Bookings
    op.drop_constraint('bookings_user_id_fkey', 'bookings', type_='foreignkey')
    op.create_foreign_key('bookings_user_id_fkey', 'bookings', 'users', ['user_id'], ['id'])

    op.drop_constraint('bookings_tour_id_fkey', 'bookings', type_='foreignkey')
    op.create_foreign_key('bookings_tour_id_fkey', 'bookings', 'tours', ['tour_id'], ['id'])

    # Tours
    op.drop_constraint('tours_company_id_fkey', 'tours', type_='foreignkey')
    op.create_foreign_key('tours_company_id_fkey', 'tours', 'companies', ['company_id'], ['id'])

    # Companies
    op.drop_constraint('companies_owner_id_fkey', 'companies', type_='foreignkey')
    op.create_foreign_key('companies_owner_id_fkey', 'companies', 'users', ['owner_id'], ['id'])