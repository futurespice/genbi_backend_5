# 🚀 Руководство по развертыванию Genbi Backend

## 📋 Содержание
1. [Быстрый старт](#быстрый-старт)
2. [Локальная разработка](#локальная-разработка)
3. [Production развертывание](#production-развертывание)
4. [Docker развертывание](#docker-развертывание)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 Быстрый старт

### Требования
- Python 3.12+
- PostgreSQL 15+
- Git

### Установка (5 минут)

```bash
# 1. Клонировать репозиторий
git clone <your-repo-url>
cd genbi_backend

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить .env
cp .env.example .env
# Отредактируйте .env и установите:
# - SECRET_KEY (сгенерируйте: openssl rand -hex 32)
# - POSTGRES_PASSWORD (ваш пароль)

# 5. Запустить БД (Docker)
docker-compose up -d db

# 6. Применить миграции
alembic upgrade head

# 7. Создать админа
python create_admin.py

# 8. Запустить сервер
uvicorn app.main:app --reload
```

Готово! Откройте http://localhost:8000/api/v1/docs

---

## 💻 Локальная разработка

### Структура проекта
```
genbi_backend/
├── app/                 # Основное приложение
│   ├── api/            # API endpoints
│   ├── core/           # Конфигурация, безопасность
│   ├── db/             # База данных
│   ├── models/         # SQLAlchemy модели
│   └── schemas/        # Pydantic схемы
├── tests/              # Тесты
├── alembic/            # Миграции БД
└── logs/               # Логи приложения
```

### Запуск тестов
```bash
# Все тесты
pytest

# С покрытием
pytest --cov=app tests/

# Конкретный файл
pytest tests/test_auth.py -v

# С логами
pytest -s
```

### Создание миграции
```bash
# Автогенерация
alembic revision --autogenerate -m "описание изменений"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1
```

### Логи
```bash
# Посмотреть логи
tail -f logs/app.log

# Логи ошибок
tail -f logs/error.log
```

---

## 🏭 Production развертывание

### Контрольный список безопасности

#### 1. Секреты
```bash
# Генерируем новый SECRET_KEY
openssl rand -hex 32

# Создаём надёжный пароль БД
openssl rand -base64 32
```

#### 2. .env файл
```env
# НЕ коммитьте .env в Git!
SECRET_KEY=<ваш_секретный_ключ>
POSTGRES_PASSWORD=<надёжный_пароль>
CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com
LOG_LEVEL=INFO
```

#### 3. CORS
В production обязательно укажите конкретные домены:
```python
# app/main.py
allow_origins=["https://yourdomain.com"],  # НЕ "*"
```

#### 4. HTTPS
Используйте Nginx + Let's Encrypt:
```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Развертывание на VPS

```bash
# 1. Подключиться к серверу
ssh user@your-server.com

# 2. Установить зависимости
sudo apt update
sudo apt install python3.12 python3-pip postgresql nginx

# 3. Клонировать проект
git clone <your-repo> /var/www/genbi
cd /var/www/genbi

# 4. Настроить виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Настроить .env
cp .env.example .env
nano .env  # Отредактировать

# 6. Настроить PostgreSQL
sudo -u postgres createuser genbi_user
sudo -u postgres createdb genbi_db
sudo -u postgres psql
postgres=# ALTER USER genbi_user WITH PASSWORD 'your_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE genbi_db TO genbi_user;

# 7. Применить миграции
alembic upgrade head

# 8. Создать админа
python create_admin.py

# 9. Настроить systemd service
sudo nano /etc/systemd/system/genbi.service
```

Содержимое `genbi.service`:
```ini
[Unit]
Description=Genbi Backend API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/genbi
Environment="PATH=/var/www/genbi/venv/bin"
ExecStart=/var/www/genbi/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

```bash
# 10. Запустить сервис
sudo systemctl daemon-reload
sudo systemctl enable genbi
sudo systemctl start genbi
sudo systemctl status genbi
```

---

## 🐳 Docker развертывание

### Разработка

```bash
# Запустить всё
docker-compose up -d

# Логи
docker-compose logs -f

# Остановить
docker-compose down

# Пересобрать
docker-compose up -d --build
```

### Production

```bash
# 1. Настроить .env
cp .env.example .env
nano .env  # Установить production значения

# 2. Собрать и запустить
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Применить миграции
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# 4. Создать админа
docker-compose -f docker-compose.prod.yml exec api python create_admin.py

# 5. Проверить статус
docker-compose -f docker-compose.prod.yml ps

# 6. Логи
docker-compose -f docker-compose.prod.yml logs -f api
```

### Управление

```bash
# Перезапустить API
docker-compose -f docker-compose.prod.yml restart api

# Остановить всё
docker-compose -f docker-compose.prod.yml down

# Остановить с удалением данных
docker-compose -f docker-compose.prod.yml down -v

# Backup БД
docker-compose -f docker-compose.prod.yml exec db pg_dump -U genbi_user genbi_db > backup.sql

# Restore БД
docker-compose -f docker-compose.prod.yml exec -T db psql -U genbi_user genbi_db < backup.sql
```

---

## 🔧 Troubleshooting

### Проблема: "Could not validate credentials"
**Решение:**
```bash
# Проверьте SECRET_KEY в .env
# Перегенерируйте токены
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@genbi.com&password=Admin123!"
```

### Проблема: "Database connection failed"
**Решение:**
```bash
# Проверьте БД
docker-compose ps db
docker-compose logs db

# Проверьте credentials
psql -h localhost -p 5433 -U genbi_user -d genbi_db
```

### Проблема: "Permission denied"
**Решение:**
```bash
# Дайте права на директорию логов
mkdir -p logs
chmod 755 logs
```

### Проблема: "Module not found"
**Решение:**
```bash
# Переустановите зависимости
pip install -r requirements.txt --force-reinstall
```

### Проблема: "Rate limit exceeded"
**Решение:**
- Увеличьте лимиты в app/core/rate_limit.py
- Или используйте другой IP

### Проблема: Миграции не применяются
**Решение:**
```bash
# Проверьте текущую ревизию
alembic current

# Посмотрите историю
alembic history

# Примените конкретную ревизию
alembic upgrade <revision_id>

# Или пересоздайте БД (ОСТОРОЖНО!)
alembic downgrade base
alembic upgrade head
```

---

## 📊 Мониторинг

### Проверка здоровья
```bash
# Health check
curl http://localhost:8000/health

# Ожидаемый ответ:
# {"status":"healthy","service":"Genbi Admin Panel"}
```

### Логи в production
```bash
# Последние 100 строк
tail -100 logs/app.log

# Логи в реальном времени
tail -f logs/app.log

# Ошибки
grep ERROR logs/app.log

# Действия админов
grep ADMIN_ACTION logs/app.log
```

### Мониторинг производительности
```bash
# CPU и память
docker stats

# Количество запросов
grep "Request:" logs/app.log | wc -l

# Средний response time (если настроен)
grep "Response:" logs/app.log | awk '{print $6}' | sort -n
```

---

## 🔐 Безопасность

### Регулярные задачи

1. **Обновление зависимостей**
```bash
pip list --outdated
pip install --upgrade <package>
```

2. **Ротация логов**
```bash
# Loguru делает это автоматически
# Настройки в app/core/logger.py
```

3. **Backup БД**
```bash
# Ежедневный backup
0 2 * * * /usr/bin/docker-compose -f /var/www/genbi/docker-compose.prod.yml exec -T db pg_dump -U genbi_user genbi_db > /backups/genbi_$(date +\%Y\%m\%d).sql
```

4. **Проверка безопасности**
```bash
# Проверка уязвимостей
pip install safety
safety check --file requirements.txt
```

---

## 📞 Поддержка

При проблемах:
1. Проверьте логи: `tail -f logs/app.log`
2. Проверьте статус: `curl http://localhost:8000/health`
3. Проверьте БД: `docker-compose ps`
4. Создайте issue в репозитории

---

**Успешного развертывания! 🚀**
