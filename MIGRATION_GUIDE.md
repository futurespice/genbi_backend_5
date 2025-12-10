# 🔄 Руководство по миграции базы данных

## Проблема с enum'ами

В существующей миграции enum значения в **UPPERCASE** (ADMIN, COMPANY), но в коде мы используем **lowercase** (admin, company).

## Решение

### Вариант 1: Пересоздать БД (рекомендуется для разработки)

```bash
# 1. Остановить приложение
# 2. Удалить БД
docker-compose down -v

# 3. Запустить заново
docker-compose up -d

# 4. Удалить старые миграции
rm alembic/versions/*

# 5. Создать новую миграцию
alembic revision --autogenerate -m "initial migration with lowercase enums"

# 6. Применить миграцию
alembic upgrade head
```

### Вариант 2: Создать миграцию для исправления (для продакшена)

```bash
# Создать миграцию
alembic revision -m "fix enum values to lowercase"
```

Содержимое миграции:

```python
"""fix enum values to lowercase

Revision ID: <generated>
Revises: fb80174b2e80
Create Date: <timestamp>
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '<generated>'
down_revision: Union[str, None] = 'fb80174b2e80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Обновляем значения в таблице users
    op.execute("""
        UPDATE users 
        SET role = LOWER(role::text)::userrole
        WHERE role IS NOT NULL
    """)
    
    # Обновляем значения в таблице bookings
    op.execute("""
        UPDATE bookings 
        SET status = LOWER(status::text)::bookingstatus
        WHERE status IS NOT NULL
    """)
    
    # Обновляем значения в таблице reviews
    op.execute("""
        UPDATE reviews 
        SET target_type = LOWER(target_type::text)::reviewtargettype
        WHERE target_type IS NOT NULL
    """)


def downgrade() -> None:
    # Возврат к uppercase
    op.execute("""
        UPDATE users 
        SET role = UPPER(role::text)::userrole
        WHERE role IS NOT NULL
    """)
    
    op.execute("""
        UPDATE bookings 
        SET status = UPPER(status::text)::bookingstatus
        WHERE status IS NOT NULL
    """)
    
    op.execute("""
        UPDATE reviews 
        SET target_type = UPPER(target_type::text)::reviewtargettype
        WHERE target_type IS NOT NULL
    """)
```

Затем:
```bash
alembic upgrade head
```

## Проверка

После применения миграции проверьте:

```bash
# Подключитесь к БД
docker exec -it <container_id> psql -U genbi_user -d genbi_db

# Проверьте значения enum
SELECT DISTINCT role FROM users;
SELECT DISTINCT status FROM bookings;
SELECT DISTINCT target_type FROM reviews;
```

Должны увидеть lowercase значения: `admin`, `company`, `client`, `pending`, `confirmed` и т.д.

## Создание первого администратора

```python
# create_admin.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import get_password_hash

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            email="admin@genbi.com",
            full_name="Admin",
            password_hash=get_password_hash("Admin123!"),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print("✅ Админ создан: admin@genbi.com / Admin123!")

if __name__ == "__main__":
    asyncio.run(create_admin())
```

Запустите:
```bash
python create_admin.py
```

## Проверка работоспособности

```bash
# 1. Регистрация нового пользователя
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234",
    "full_name": "Test User",
    "role": "client"
  }'

# 2. Логин
curl -X POST "http://localhost:8000/api/v1/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234"
  }'
```

Если всё работает - миграция прошла успешно! ✅
