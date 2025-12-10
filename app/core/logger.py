import sys
from loguru import logger
from app.core.config import settings

# Удаляем дефолтный handler
logger.remove()

# Добавляем только stdout (для Vercel)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=False  # Vercel не поддерживает цвета
)

# В production НЕ пишем в файлы (Vercel read-only)
# Логи автоматически попадают в Vercel Logs


def log_auth_attempt(email: str, success: bool, ip: str):
    """Логирование попыток входа"""
    if success:
        logger.info(f"✅ Successful login: {email} from {ip}")
    else:
        logger.warning(f"❌ Failed login attempt: {email} from {ip}")


def log_admin_action(admin_email: str, action: str, details: str = ""):
    """Логирование действий администратора"""
    logger.info(f"👤 Admin {admin_email} | Action: {action} | {details}")


def log_booking_action(user_id: int, action: str, booking_id: int = None, details: str = ""):
    """Логирование действий с бронированиями"""
    logger.info(f"📅 User {user_id} | Action: {action} | Booking: {booking_id} | {details}")


def log_user_action(user_id: int, action: str, details: str = ""):
    """Логирование действий пользователя"""
    logger.info(f"👤 User {user_id} | Action: {action} | {details}")
