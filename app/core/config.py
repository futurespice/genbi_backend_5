from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Genbi Admin Panel"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = "development"

    # БД
    POSTGRES_USER: str = "genbi_user"
    POSTGRES_PASSWORD: str = "genbi_pass"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_DB: str = "genbi_db"
    POSTGRES_PORT: str = "5433"

    CONNECTION_STRING: Optional[str] = None

    @property
    def DATABASE_URL(self) -> str:
        if self.CONNECTION_STRING:
            url = self.CONNECTION_STRING.replace("postgresql://", "postgresql+asyncpg://")
            url = url.replace("?sslmode=require", "?ssl=require")
            url = url.replace("&channel_binding=require", "")
            url = url.replace("&sslmode=require", "")
            return url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Безопасность
    SECRET_KEY: str = "dev-secret-key-CHANGE-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    # ==========================================
    # 🔥 ИСПРАВЛЕННЫЙ CORS
    # ==========================================
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """
        Возвращает список разрешенных origins для CORS
        """
        origins = []

        if self.ENVIRONMENT == "production":
            # Production - только конкретные домены
            origins = [
                "https://genbi-backend-5.vercel.app",
                "https://yourdomain.com",
                "https://admin.yourdomain.com",
                "https://www.yourdomain.com",
            ]
        elif self.ENVIRONMENT == "staging":
            # Staging
            origins = [
                "https://staging.yourdomain.com",
                "https://genbi-staging.vercel.app",
            ]
        else:
            # Development - разрешаем localhost и 127.0.0.1
            origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://localhost:8080",
                "http://localhost:8081",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081",
                # Добавляем Vercel preview URLs для разработки
                "https://genbi-backend-5.vercel.app",
            ]

        return origins

    # ==========================================
    # Allowed Hosts (только для production)
    # ==========================================
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """
        Список разрешенных хостов
        Используется только в production
        """
        return [
            "genbi-backend-5.vercel.app",
            "yourdomain.com",
            "www.yourdomain.com",
            "admin.yourdomain.com",
            "api.yourdomain.com",
        ]

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: str = "5/minute"
    REGISTER_RATE_LIMIT: str = "3/hour"
    API_RATE_LIMIT: str = "100/minute"

    # Бизнес-правила
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 30
    MIN_PASSWORD_LENGTH: int = 8

    # Tours
    MAX_TOUR_CAPACITY: int = 1000
    MIN_ADVANCE_BOOKING_HOURS: int = 24

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()