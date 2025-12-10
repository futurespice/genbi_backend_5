from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from app.api import deps
from app.core.logger import logger, log_admin_action
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.pagination import PaginationParams, PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserResponse])
@limiter.limit("100/minute")
async def read_users(
    request: Request,
    pagination: PaginationParams = Depends(),
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить список пользователей (только для админа)
    
    Фильтры:
    - role: фильтр по роли
    - is_active: фильтр по активности
    - search: поиск по имени или email
    """
    query = select(User)
    
    # Применяем фильтры
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    # Подсчёт total
    count_query = select(User.id)
    if role:
        count_query = count_query.filter(User.role == role)
    if is_active is not None:
        count_query = count_query.filter(User.is_active == is_active)
    if search:
        count_query = count_query.filter(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    total_result = await db.execute(count_query)
    total = len(total_result.all())
    
    # Получаем users с пагинацией
    query = query.offset(pagination.skip).limit(pagination.limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    log_admin_action(
        current_user.id,
        current_user.email,
        "list_users",
        f"Filters: role={role}, search={search}, total={total}"
    )
    
    return PaginatedResponse.create(
        items=users,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page
    )


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить пользователя по ID (только для админа)
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Обновить пользователя (только для админа)
    
    ⚠️ ЗАЩИТА: Нельзя изменить собственную роль!
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ КРИТИЧЕСКАЯ ПРОВЕРКА: Нельзя изменить свою роль!
    if user_id == current_user.id and user_update.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )
    
    # Проверка уникальности email
    if user_update.email and user_update.email != user.email:
        existing = await db.execute(
            select(User).filter(User.email == user_update.email)
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    # Проверка уникальности phone
    if user_update.phone and user_update.phone != user.phone:
        existing = await db.execute(
            select(User).filter(User.phone == user_update.phone)
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="Phone number already registered"
            )
    
    # Обновляем поля
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    log_admin_action(
        current_user.id,
        current_user.email,
        "update_user",
        f"Updated user {user.email} (ID: {user_id}). Fields: {list(update_data.keys())}"
    )
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Удалить пользователя (только для админа)
    
    ⚠️ ЗАЩИТА: Нельзя удалить себя!
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete yourself"
        )
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    
    log_admin_action(
        current_user.id,
        current_user.email,
        "delete_user",
        f"Deleted user {user.email} (ID: {user_id})"
    )
    
    return {"detail": "User deleted successfully"}
