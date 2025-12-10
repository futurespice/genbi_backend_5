from pydantic import BaseModel
from datetime import datetime
from typing import Literal

class BookingBase(BaseModel):
    tour_id: int
    participants_count: int = 1
    date: datetime

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    # ✅ ИСПРАВЛЕНО: используем Literal
    status: Literal['pending', 'confirmed', 'paid', 'cancelled']

class BookingResponse(BookingBase):
    id: int
    user_id: int
    status: Literal['pending', 'confirmed', 'paid', 'cancelled']
    created_at: datetime

    class Config:
        from_attributes = True
