"""
Rate Limiting для защиты API от злоупотреблений
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import logger


# Создаём limiter с использованием IP адреса клиента
limiter = Limiter(key_func=get_remote_address)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования rate limit превышений"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RateLimitExceeded as e:
            client_ip = get_remote_address(request)
            logger.warning(
                f"RATE_LIMIT_EXCEEDED | IP: {client_ip} | "
                f"Path: {request.url.path} | Limit: {e.detail}"
            )
            raise


# Декоратор для применения rate limiting к эндпоинтам
def rate_limit(limit: str):
    """
    Декоратор для rate limiting
    
    Примеры использования:
    - "5/minute" - 5 запросов в минуту
    - "100/hour" - 100 запросов в час
    - "1000/day" - 1000 запросов в день
    """
    return limiter.limit(limit)


# Предустановленные лимиты
def login_rate_limit():
    """5 попыток входа в минуту"""
    return rate_limit("5/minute")


def register_rate_limit():
    """3 регистрации в час"""
    return rate_limit("3/hour")


def api_rate_limit():
    """100 запросов в минуту для обычных операций"""
    return rate_limit("100/minute")


def strict_rate_limit():
    """10 запросов в минуту для критичных операций"""
    return rate_limit("10/minute")


__all__ = [
    "limiter",
    "RateLimitMiddleware",
    "rate_limit",
    "login_rate_limit",
    "register_rate_limit",
    "api_rate_limit",
    "strict_rate_limit",
]
