from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ✅ ИСПРАВЛЕНО: echo только в development
# В production echo=True может привести к SQL injection через логи
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT != "production",  # ✅ КРИТИЧНО! echo=False в production
    pool_pre_ping=True,  # ✅ Проверка соединения перед использованием
    pool_size=20,  # ✅ Размер пула соединений
    max_overflow=0,  # ✅ Не создавать дополнительные соединения
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session