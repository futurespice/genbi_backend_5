from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class ReviewBase(BaseModel):
    # ✅ ИСПРАВЛЕНО: используем Literal
    target_type: Literal['tour', 'company']
    target_id: int
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: str | None = None

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: int
    author_id: int
    created_at: datetime
    is_moderated: bool

    class Config:
        from_attributes = True
