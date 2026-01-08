from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class TourBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    image_url: str | None = None
    description: str | None = None
    schedule: Dict[str, Any] | None = None
    price: float = Field(..., gt=0, description="Цена должна быть больше 0")
    location: str = Field(..., min_length=2, max_length=200)
    duration: str = Field(..., min_length=2, max_length=100)
    capacity: int = Field(default=50, ge=1, le=1000, description="Вместимость от 1 до 1000")

    # Координаты
    latitude: float | None = Field(None, ge=-90, le=90, description="Широта (от -90 до 90)")
    longitude: float | None = Field(None, ge=-180, le=180, description="Долгота (от -180 до 180)")


class TourCreate(TourBase):
    company_id: int


class TourUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    image_url: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[Dict[str, Any]] = None
    price: Optional[float] = Field(None, gt=0)
    location: Optional[str] = Field(None, min_length=2, max_length=200)
    duration: Optional[str] = Field(None, min_length=2, max_length=100)
    capacity: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class TourResponse(TourBase):
    id: int
    company_id: int | None = None  # ✅ ИСПРАВЛЕНО: может быть NULL если компания удалена
    rating: float
    is_active: bool

    class Config:
        from_attributes = True