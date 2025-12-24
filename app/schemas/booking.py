from pydantic import BaseModel
from datetime import datetime
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.tour import TourResponse
    from app.schemas.company import CompanyResponse
    from app.schemas.user import UserResponse


class BookingBase(BaseModel):
    tour_id: int
    participants_count: int = 1
    date: datetime


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    status: Literal['pending', 'confirmed', 'paid', 'cancelled']


class BookingResponse(BookingBase):
    id: int
    user_id: int
    status: Literal['pending', 'confirmed', 'paid', 'cancelled']
    created_at: datetime

    class Config:
        from_attributes = True


# ✅ НОВОЕ: Детальная информация о бронировании для страницы по ID
class BookingDetailResponse(BaseModel):
    """
    Расширенная информация о бронировании

    Используется для детальной страницы бронирования (GET /bookings/{id})
    Включает полную информацию о:
    - Бронировании
    - Туре
    - Компании
    - Пользователе (только для админа/компании)
    """
    id: int
    tour_id: int
    user_id: int
    participants_count: int
    date: datetime
    status: Literal['pending', 'confirmed', 'paid', 'cancelled']
    created_at: datetime

    # Вложенные объекты
    tour: 'TourResponse'
    company: 'CompanyResponse'
    user: 'UserResponse | None' = None  # Только для админа/владельца компании

    class Config:
        from_attributes = True


# Для избежания circular imports
from app.schemas.tour import TourResponse
from app.schemas.company import CompanyResponse
from app.schemas.user import UserResponse

BookingDetailResponse.model_rebuild()