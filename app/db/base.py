# Импортируем Base
from app.db.base_class import Base

# Импортируем модели в правильном порядке (важно для relationships!)
# 1. Сначала независимые модели
from app.models.user import User

# 2. Модели, зависящие от User
from app.models.company import Company

# 3. Модели, зависящие от Company
from app.models.tour import Tour

# 4. Модели, зависящие от Tour и User
from app.models.booking import Booking
from app.models.review import Review

# Экспортируем для удобства
__all__ = ["Base", "User", "Company", "Tour", "Booking", "Review"]
