from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class CompanyApplicationBase(BaseModel):
    """Базовая схема заявки"""
    company_name: str = Field(..., min_length=2, max_length=200)
    company_address: str = Field(..., min_length=5, max_length=300)
    company_website: str | None = Field(None, max_length=200)
    work_hours: str | None = Field(None, max_length=100)


class CompanyApplicationCreate(CompanyApplicationBase):
    """Создание заявки - только данные компании"""
    pass


class CompanyApplicationResponse(CompanyApplicationBase):
    """Ответ с информацией о заявке"""
    id: int
    user_id: int
    status: Literal['pending', 'approved', 'rejected']
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_admin_id: int | None = None
    rejection_reason: str | None = None

    class Config:
        from_attributes = True


class CompanyApplicationReview(BaseModel):
    """Модерация заявки"""
    rejection_reason: str | None = Field(None, max_length=500)