"""
Система логирования для Genbi Backend
"""
import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings

# Создаём директорию для логов
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Удаляем дефолтный обработчик
logger.remove()

# Добавляем консольный вывод с цветами
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=getattr(settings, "LOG_LEVEL", "INFO"),
)

# Добавляем файловый вывод с ротацией
logger.add(
    getattr(settings, "LOG_FILE", "logs/app.log"),
    rotation="500 MB",  # Новый файл каждые 500MB
    retention="10 days",  # Хранить логи 10 дней
    compression="zip",  # Сжимать старые логи
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
)

# Отдельный файл для ошибок
logger.add(
    "logs/error.log",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
)


def log_user_action(user_id: int, user_email: str, action: str, details: str = ""):
    """Логирование действий пользователей"""
    logger.info(f"USER_ACTION | User ID: {user_id} ({user_email}) | Action: {action} | Details: {details}")


def log_admin_action(admin_id: int, admin_email: str, action: str, details: str = ""):
    """Логирование действий администраторов"""
    logger.warning(f"ADMIN_ACTION | Admin ID: {admin_id} ({admin_email}) | Action: {action} | Details: {details}")


def log_company_action(company_id: int, user_id: int, action: str, details: str = ""):
    """Логирование действий компаний"""
    logger.info(f"COMPANY_ACTION | Company ID: {company_id} | User ID: {user_id} | Action: {action} | Details: {details}")


def log_auth_attempt(email: str, success: bool, ip: str = "unknown"):
    """Логирование попыток входа"""
    level = "info" if success else "warning"
    status = "SUCCESS" if success else "FAILED"
    getattr(logger, level)(f"AUTH_ATTEMPT | Email: {email} | Status: {status} | IP: {ip}")


def log_booking_action(booking_id: int, user_id: int, action: str, details: str = ""):
    """Логирование действий с бронированиями"""
    logger.info(f"BOOKING_ACTION | Booking ID: {booking_id} | User ID: {user_id} | Action: {action} | Details: {details}")


def log_review_action(review_id: int, user_id: int, action: str, details: str = ""):
    """Логирование действий с отзывами"""
    logger.info(f"REVIEW_ACTION | Review ID: {review_id} | User ID: {user_id} | Action: {action} | Details: {details}")


# Экспортируем основной логгер
__all__ = [
    "logger",
    "log_user_action",
    "log_admin_action",
    "log_company_action",
    "log_auth_attempt",
    "log_booking_action",
    "log_review_action",
]
