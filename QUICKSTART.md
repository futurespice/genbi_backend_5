# ⚡ Быстрый старт проекта

## 1️⃣ Скопируйте файлы в свой проект

Замените следующие файлы в вашем проекте на исправленные версии из `/home/claude/genbi_backend/`:

```bash
# Основные файлы
app/core/config.py
app/core/security.py
app/api/deps.py
app/main.py

# Модели
app/models/enums.py
app/models/user.py
app/models/company.py
app/models/tour.py
app/models/booking.py
app/models/review.py

# Схемы
app/schemas/user.py
app/schemas/company.py
app/schemas/tour.py
app/schemas/booking.py
app/schemas/review.py
app/schemas/token.py
app/schemas/pagination.py  # НОВЫЙ

# Эндпоинты
app/api/v1/api.py
app/api/v1/endpoints/auth.py
app/api/v1/endpoints/users.py     # НОВЫЙ
app/api/v1/endpoints/companies.py
app/api/v1/endpoints/tours.py
app/api/v1/endpoints/bookings.py
app/api/v1/endpoints/reviews.py

# Конфигурация
.env.example
.gitignore
README.md
create_admin.py  # НОВЫЙ
```

## 2️⃣ Обновите .env

```bash
cp .env.example .env
```

Отредактируйте `.env`:

**Для локальной БД:**
```env
POSTGRES_SERVER=localhost
POSTGRES_PORT=5433
SECRET_KEY=<ваш-новый-ключ>
```

**Для Neon (облачная БД):**
```env
CONNECTION_STRING=postgresql://...
SECRET_KEY=<ваш-новый-ключ>
```

Сгенерируйте новый SECRET_KEY:
```bash
openssl rand -hex 32
```

## 3️⃣ Пересоздайте БД (рекомендуется)

```bash
# Остановить и удалить контейнер БД
docker-compose down -v

# Запустить заново
docker-compose up -d

# Удалить старые миграции
rm alembic/versions/*

# Создать новую миграцию
alembic revision --autogenerate -m "initial migration with lowercase enums"

# Применить миграцию
alembic upgrade head
```

## 4️⃣ Создайте первого администратора

```bash
python create_admin.py
```

Будет создан:
- **Email:** admin@genbi.com
- **Пароль:** Admin123!

## 5️⃣ Запустите сервер

```bash
uvicorn app.main:app --reload
```

## 6️⃣ Проверьте работу

Откройте в браузере:
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/api/v1/docs

### Тест регистрации

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234",
    "full_name": "Test User",
    "role": "client"
  }'
```

### Тест логина

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@genbi.com",
    "password": "Admin123!"
  }'
```

Если получили токены - всё работает! ✅

## 🎉 Готово!

Теперь у вас:
- ✅ Исправлены все критические ошибки
- ✅ Добавлена пагинация
- ✅ Работает регистрация и логин
- ✅ Refresh токены
- ✅ Валидация бизнес-логики
- ✅ Управление пользователями
- ✅ CORS настроен
- ✅ Обработка ошибок

## 🚨 Возможные проблемы

### Ошибка подключения к БД

Проверьте, что PostgreSQL запущен:
```bash
docker-compose ps
```

### Ошибка импорта

Убедитесь, что все `__init__.py` файлы на месте.

### Ошибка в enum

Если используете старую БД - следуйте инструкциям в `MIGRATION_GUIDE.md`.

## 📚 Что дальше?

1. Прочитайте полный `README.md`
2. Изучите документацию API в Swagger
3. Добавьте тесты
4. Настройте CI/CD
5. Деплой на production
