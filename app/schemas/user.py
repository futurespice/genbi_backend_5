from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Literal


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    role: Literal['admin', 'company', 'client'] = 'client'


class UserCreate(BaseModel):
    """
    Регистрация пользователя - ТОЛЬКО CLIENT
    Для получения роли COMPANY нужно подать заявку через /applications
    """
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    password: str = Field(..., min_length=8, max_length=100)

    # ✅ УБРАЛИ ВЫБОР РОЛИ - всегда будет client

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен быть минимум 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.islower() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    role: Optional[Literal['admin', 'company', 'client']] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str