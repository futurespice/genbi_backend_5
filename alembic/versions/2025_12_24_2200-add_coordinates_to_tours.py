"""Add latitude and longitude to tours

Revision ID: add_coordinates_to_tours
Revises: add_company_applications
Create Date: 2025-12-24 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_coordinates_to_tours'
down_revision: Union[str, None] = 'add_company_applications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем координаты в таблицу tours
    op.add_column('tours', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('tours', sa.Column('longitude', sa.Float(), nullable=True))

    # Создаем индексы для поиска по координатам (для будущих фич типа "туры рядом со мной")
    op.create_index('ix_tours_latitude', 'tours', ['latitude'])
    op.create_index('ix_tours_longitude', 'tours', ['longitude'])


def downgrade() -> None:
    # Удаляем индексы
    op.drop_index('ix_tours_longitude', table_name='tours')
    op.drop_index('ix_tours_latitude', table_name='tours')

    # Удаляем колонки
    op.drop_column('tours', 'longitude')
    op.drop_column('tours', 'latitude')