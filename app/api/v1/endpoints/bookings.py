from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_
from datetime import datetime, timezone, timedelta

from app.api import deps
from app.core.logger import logger, log_booking_action
from app.core.rate_limit import limiter
from app.core.config import settings
from app.db.session import get_db
from app.models.booking import Booking
from app.models.tour import Tour
from app.models.company import Company
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse, BookingUpdate, BookingDetailResponse
from app.schemas.pagination import PaginationParams, PaginatedResponse

router = APIRouter()


@router.post("/", response_model=BookingResponse)
@limiter.limit("20/minute")
async def create_booking(
        request: Request,
        booking_in: BookingCreate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Создать бронирование

    ✅ ИСПРАВЛЕНО: Race condition устранен через SELECT FOR UPDATE

    Проверки:
    - Тур существует и активен
    - Дата не в прошлом
    - Количество участников > 0
    - Нет дубликата
    - Достаточно capacity (с блокировкой!)
    """

    # ============================================
    # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Транзакционная блокировка
    # ============================================
    async with db.begin():  # Начинаем транзакцию
        # Проверка тура с блокировкой строки (FOR UPDATE)
        result = await db.execute(
            select(Tour)
            .filter(Tour.id == booking_in.tour_id)
            .with_for_update()  # ✅ БЛОКИРОВКА! Другие транзакции подождут
        )
        tour = result.scalars().first()

        if not tour:
            raise HTTPException(status_code=404, detail="Tour not found")

        if not tour.is_active:
            raise HTTPException(status_code=400, detail="Tour is not active")

        # Проверка даты
        min_booking_time = datetime.now(timezone.utc) + timedelta(hours=settings.MIN_ADVANCE_BOOKING_HOURS)
        if booking_in.date < min_booking_time:
            raise HTTPException(
                status_code=400,
                detail=f"Bookings must be made at least {settings.MIN_ADVANCE_BOOKING_HOURS} hours in advance"
            )

        # Проверка участников
        if booking_in.participants_count < 1:
            raise HTTPException(
                status_code=400,
                detail="Participants count must be at least 1"
            )

        # ✅ CAPACITY CHECK С БЛОКИРОВКОЙ - КРИТИЧНО!
        # Блокируем все бронирования на этот тур и дату
        existing_bookings = await db.execute(
            select(func.sum(Booking.participants_count))
            .where(Booking.tour_id == booking_in.tour_id)
            .where(Booking.date == booking_in.date)
            .where(Booking.status.in_([
                'pending',
                'confirmed',
                'paid'
            ]))
            .with_for_update()  # ✅ БЛОКИРОВКА! Защита от race condition
        )
        total_participants = existing_bookings.scalar() or 0

        available_capacity = tour.capacity - total_participants

        if booking_in.participants_count > available_capacity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough capacity. Available: {available_capacity}, Requested: {booking_in.participants_count}"
            )

        # Проверка дубликата
        duplicate = await db.execute(
            select(Booking)
            .where(Booking.tour_id == booking_in.tour_id)
            .where(Booking.user_id == current_user.id)
            .where(Booking.date == booking_in.date)
            .where(Booking.status != 'cancelled')
        )
        if duplicate.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="You already have a booking for this tour on this date"
            )

        # Создание бронирования
        booking = Booking(
            **booking_in.model_dump(),
            user_id=current_user.id,
            status='pending'
        )
        db.add(booking)
        # ✅ commit произойдет автоматически при выходе из with db.begin()

    # Обновляем объект после коммита
    await db.refresh(booking)

    log_booking_action(
        booking.id,
        current_user.id,
        "create",
        f"Tour: {tour.title}, Participants: {booking.participants_count}, Date: {booking.date}"
    )

    return booking


@router.get("/", response_model=PaginatedResponse[BookingResponse])
async def read_bookings(
        pagination: PaginationParams = Depends(),
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Список бронирований (с RBAC)

    - CLIENT: только свои
    - COMPANY: бронирования своих туров
    - ADMIN: все
    """
    query = select(Booking)
    count_query = select(Booking.id)

    if current_user.role == 'client':
        query = query.filter(Booking.user_id == current_user.id)
        count_query = count_query.filter(Booking.user_id == current_user.id)

    elif current_user.role == 'company':
        query = (
            query
            .options(selectinload(Booking.tour).selectinload(Tour.company))
            .join(Tour)
            .join(Company)
            .filter(Company.owner_id == current_user.id)
        )
        count_query = (
            count_query
            .join(Tour, Booking.tour_id == Tour.id)
            .join(Company, Tour.company_id == Company.id)
            .filter(Company.owner_id == current_user.id)
        )

    # Подсчёт
    total_result = await db.execute(count_query)
    total = len(total_result.all())

    # Получение с пагинацией
    query = query.offset(pagination.skip).limit(pagination.limit)
    result = await db.execute(query)
    bookings = result.scalars().all()

    return PaginatedResponse.create(
        items=bookings,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page
    )


@router.get("/{booking_id}", response_model=BookingDetailResponse)
async def read_booking(
        booking_id: int,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить детальную информацию о бронировании
    """
    query = (
        select(Booking)
        .options(
            selectinload(Booking.tour).selectinload(Tour.company),
            selectinload(Booking.user)
        )
        .filter(Booking.id == booking_id)
    )
    result = await db.execute(query)
    booking = result.scalars().first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Проверка прав
    is_owner = booking.user_id == current_user.id
    is_company_owner = booking.tour.company and booking.tour.company.owner_id == current_user.id
    is_admin = current_user.role == 'admin'

    if not (is_owner or is_company_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Формируем детальный ответ
    response_data = {
        "id": booking.id,
        "tour_id": booking.tour_id,
        "user_id": booking.user_id,
        "participants_count": booking.participants_count,
        "date": booking.date,
        "status": booking.status,
        "created_at": booking.created_at,
        "tour": booking.tour,
        "company": booking.tour.company if booking.tour.company else None,
    }

    # Информация о пользователе - только для админа или владельца компании
    if is_admin or is_company_owner:
        response_data["user"] = booking.user

    return response_data


@router.patch("/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
        booking_id: int,
        status_update: BookingUpdate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Изменить статус бронирования

    Права:
    - CLIENT: может только отменить (CANCELLED)
    - COMPANY/ADMIN: могут менять любой статус

    ✅ Проверка: нельзя изменить CANCELLED бронирование
    """
    query = (
        select(Booking)
        .options(selectinload(Booking.tour).selectinload(Tour.company))
        .filter(Booking.id == booking_id)
    )
    result = await db.execute(query)
    booking = result.scalars().first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # ✅ Нельзя изменить отменённое бронирование
    if booking.status == 'cancelled':
        raise HTTPException(
            status_code=400,
            detail="Cannot modify cancelled booking"
        )

    # Проверка прав
    is_admin = current_user.role == 'admin'
    is_company_owner = booking.tour.company and booking.tour.company.owner_id == current_user.id
    is_booking_owner = booking.user_id == current_user.id

    # Клиент может только отменить
    if is_booking_owner and not (is_admin or is_company_owner):
        if status_update.status != 'cancelled':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clients can only cancel bookings"
            )

    # Компания и админ могут менять любой статус
    if not (is_admin or is_company_owner or is_booking_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    old_status = booking.status
    booking.status = status_update.status
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    log_booking_action(
        booking.id,
        current_user.id,
        "update_status",
        f"Status changed: {old_status} → {booking.status}"
    )

    return booking


@router.delete("/{booking_id}")
async def delete_booking(
        booking_id: int,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Удалить бронирование (только ADMIN)
    """
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete bookings"
        )

    result = await db.execute(select(Booking).filter(Booking.id == booking_id))
    booking = result.scalars().first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    await db.delete(booking)
    await db.commit()

    log_booking_action(
        booking_id,
        current_user.id,
        "delete",
        f"Booking deleted by admin"
    )

    return {"detail": "Booking deleted successfully"}