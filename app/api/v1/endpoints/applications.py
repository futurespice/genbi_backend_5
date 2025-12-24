from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timezone

from app.api import deps
from app.core.logger import logger, log_admin_action
from app.db.session import get_db
from app.models.company_application import CompanyApplication
from app.models.company import Company
from app.models.user import User
from app.schemas.company_application import (
    CompanyApplicationCreate,
    CompanyApplicationResponse,
    CompanyApplicationReview
)
from app.schemas.pagination import PaginatedResponse, PaginationParams

router = APIRouter()


@router.post("/", response_model=CompanyApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
        application_in: CompanyApplicationCreate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Подать заявку на регистрацию компании

    ✅ Может подать только пользователь с ролью 'client'
    ⚠️ Нельзя подать повторную заявку, если есть активная
    ⚠️ Нельзя подать заявку, если уже есть компания
    """

    # Проверка: только client может подавать заявки
    if current_user.role != 'client':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заявку могут подавать только пользователи с ролью 'client'"
        )

    # Проверка: нет ли уже компании у пользователя
    result = await db.execute(
        select(Company).filter(Company.owner_id == current_user.id)
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас уже есть компания"
        )

    # Проверка: нет ли активной заявки
    result = await db.execute(
        select(CompanyApplication).filter(
            CompanyApplication.user_id == current_user.id,
            CompanyApplication.status == 'pending'
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас уже есть активная заявка. Дождитесь её рассмотрения."
        )

    # Создание заявки
    application = CompanyApplication(
        **application_in.model_dump(),
        user_id=current_user.id,
        status='pending'
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    logger.info(
        f"New company application created: ID={application.id}, "
        f"User={current_user.email}, Company={application.company_name}"
    )

    return application


@router.get("/", response_model=PaginatedResponse[CompanyApplicationResponse])
async def get_applications(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        status: str | None = Query(None, description="Фильтр по статусу"),
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить список заявок

    - CLIENT: видит только свои заявки
    - ADMIN: видит все заявки с фильтрацией
    """

    pagination = PaginationParams(page=page, per_page=per_page)

    query = select(CompanyApplication)
    count_query = select(func.count(CompanyApplication.id))

    # CLIENT видит только свои заявки
    if current_user.role == 'client':
        query = query.filter(CompanyApplication.user_id == current_user.id)
        count_query = count_query.filter(CompanyApplication.user_id == current_user.id)
    # COMPANY тоже видит только свои (на случай если есть старые заявки)
    elif current_user.role == 'company':
        query = query.filter(CompanyApplication.user_id == current_user.id)
        count_query = count_query.filter(CompanyApplication.user_id == current_user.id)
    # ADMIN видит все

    # Фильтр по статусу
    if status and current_user.role == 'admin':
        query = query.filter(CompanyApplication.status == status)
        count_query = count_query.filter(CompanyApplication.status == status)

    # Подсчёт
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Пагинация
    query = query.offset(pagination.skip).limit(pagination.limit).order_by(
        CompanyApplication.created_at.desc()
    )
    result = await db.execute(query)
    applications = result.scalars().all()

    return PaginatedResponse.create(
        items=applications,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{application_id}", response_model=CompanyApplicationResponse)
async def get_application(
        application_id: int,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """Получить заявку по ID"""

    result = await db.execute(
        select(CompanyApplication).filter(CompanyApplication.id == application_id)
    )
    application = result.scalars().first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    # Проверка прав: только автор или админ
    if current_user.role != 'admin' and application.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра этой заявки"
        )

    return application


@router.post("/{application_id}/approve", response_model=CompanyApplicationResponse)
async def approve_application(
        application_id: int,
        current_user: User = Depends(deps.get_current_admin),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Одобрить заявку (только ADMIN)

    При одобрении:
    1. Создается компания
    2. Пользователь получает роль 'company'
    3. Статус заявки меняется на 'approved'
    """

    result = await db.execute(
        select(CompanyApplication).filter(CompanyApplication.id == application_id)
    )
    application = result.scalars().first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    if application.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Заявка уже обработана. Статус: {application.status}"
        )

    # Получаем пользователя
    result = await db.execute(select(User).filter(User.id == application.user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    # Проверка: нет ли уже компании
    result = await db.execute(
        select(Company).filter(Company.owner_id == user.id)
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя уже есть компания"
        )

    # 1. Создаем компанию
    company = Company(
        name=application.company_name,
        address=application.company_address,
        website=application.company_website,
        work_hours=application.work_hours,
        owner_id=user.id
    )
    db.add(company)

    # 2. Меняем роль пользователя
    user.role = 'company'
    db.add(user)

    # 3. Обновляем статус заявки
    application.status = 'approved'
    application.reviewed_at = datetime.now(timezone.utc)
    application.reviewed_by_admin_id = current_user.id
    db.add(application)

    await db.commit()
    await db.refresh(application)

    log_admin_action(
        current_user.id,
        current_user.email,
        "approve_company_application",
        f"Approved application ID={application.id}, created company '{company.name}' "
        f"for user {user.email}"
    )

    logger.info(
        f"✅ Application approved: ID={application.id}, "
        f"Company='{company.name}', User={user.email} → role changed to 'company'"
    )

    return application


@router.post("/{application_id}/reject", response_model=CompanyApplicationResponse)
async def reject_application(
        application_id: int,
        review: CompanyApplicationReview,
        current_user: User = Depends(deps.get_current_admin),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Отклонить заявку (только ADMIN)

    ⚠️ Обязательно указать причину отклонения
    """

    result = await db.execute(
        select(CompanyApplication).filter(CompanyApplication.id == application_id)
    )
    application = result.scalars().first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    if application.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Заявка уже обработана. Статус: {application.status}"
        )

    if not review.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите причину отклонения"
        )

    # Обновляем статус заявки
    application.status = 'rejected'
    application.reviewed_at = datetime.now(timezone.utc)
    application.reviewed_by_admin_id = current_user.id
    application.rejection_reason = review.rejection_reason
    db.add(application)

    await db.commit()
    await db.refresh(application)

    log_admin_action(
        current_user.id,
        current_user.email,
        "reject_company_application",
        f"Rejected application ID={application.id}, Reason: {review.rejection_reason}"
    )

    logger.info(
        f"❌ Application rejected: ID={application.id}, Reason: {review.rejection_reason}"
    )

    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
        application_id: int,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> None:
    """
    Удалить заявку

    - CLIENT может удалить только свою заявку со статусом 'pending' или 'rejected'
    - ADMIN может удалить любую заявку
    """

    result = await db.execute(
        select(CompanyApplication).filter(CompanyApplication.id == application_id)
    )
    application = result.scalars().first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    # Проверка прав
    is_owner = application.user_id == current_user.id
    is_admin = current_user.role == 'admin'

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления этой заявки"
        )

    # CLIENT может удалить только pending или rejected
    if is_owner and not is_admin:
        if application.status == 'approved':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить одобренную заявку"
            )

    await db.delete(application)
    await db.commit()

    logger.info(f"Application deleted: ID={application.id}")