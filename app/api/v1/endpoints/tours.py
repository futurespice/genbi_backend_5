from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_

from app.api import deps
from app.db.session import get_db
from app.models.tour import Tour
from app.models.company import Company
from app.models.user import User
from app.schemas.tour import TourCreate, TourResponse, TourUpdate
from app.schemas.pagination import PaginatedResponse, PaginationParams

router = APIRouter()


@router.post("/", response_model=TourResponse, status_code=status.HTTP_201_CREATED)
async def create_tour(
        tour_in: TourCreate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Создать тур

    Проверка: пользователь должен быть владельцем компании или админом

    - **title**: Название тура
    - **description**: Описание
    - **price**: Цена
    - **location**: Локация
    - **duration**: Продолжительность
    - **company_id**: ID компании
    """

    # Проверка существования компании
    result = await db.execute(select(Company).filter(Company.id == tour_in.company_id))
    company = result.scalars().first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )

    # Проверка прав
    if company.owner_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для добавления туров в эту компанию"
        )

    # Валидация цены
    if tour_in.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Цена должна быть больше нуля"
        )

    tour = Tour(**tour_in.model_dump(), rating=0.0)
    db.add(tour)
    await db.commit()
    await db.refresh(tour)

    return tour


@router.get("/", response_model=PaginatedResponse[TourResponse])
async def get_tours(
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(20, ge=1, le=100, description="Элементов на странице"),
        location: str | None = Query(None, description="Фильтр по локации"),
        min_price: float | None = Query(None, ge=0, description="Минимальная цена"),
        max_price: float | None = Query(None, ge=0, description="Максимальная цена"),
        search: str | None = Query(None, description="Поиск по названию или описанию"),
        sort_by: str | None = Query(None, enum=["price_asc", "price_desc", "rating", "newest"],
                                    description="Сортировка"),
        company_id: int | None = Query(None, description="Фильтр по компании"),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить список туров с фильтрацией и пагинацией

    - **page**: Номер страницы
    - **per_page**: Количество элементов на странице
    - **location**: Фильтр по локации
    - **min_price**: Минимальная цена
    - **max_price**: Максимальная цена
    - **search**: Поиск по названию или описанию
    - **sort_by**: Сортировка (price_asc, price_desc, rating, newest)
    - **company_id**: Фильтр по компании
    """

    pagination = PaginationParams(page=page, per_page=per_page)

    # Базовый запрос
    query = select(Tour)
    count_query = select(func.count(Tour.id))

    # Фильтрация
    if location:
        location_filter = Tour.location.ilike(f"%{location}%")
        query = query.filter(location_filter)
        count_query = count_query.filter(location_filter)

    if min_price is not None:
        price_filter = Tour.price >= min_price
        query = query.filter(price_filter)
        count_query = count_query.filter(price_filter)

    if max_price is not None:
        price_filter = Tour.price <= max_price
        query = query.filter(price_filter)
        count_query = count_query.filter(price_filter)

    if search:
        search_filter = or_(
            Tour.title.ilike(f"%{search}%"),
            Tour.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
        count_query = count_query.filter(search_filter)

    if company_id:
        company_filter = Tour.company_id == company_id
        query = query.filter(company_filter)
        count_query = count_query.filter(company_filter)

    # Сортировка
    if sort_by == "price_asc":
        query = query.order_by(Tour.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Tour.price.desc())
    elif sort_by == "rating":
        query = query.order_by(Tour.rating.desc())
    elif sort_by == "newest":
        query = query.order_by(Tour.id.desc())
    else:
        query = query.order_by(Tour.id.desc())  # По умолчанию - новые первые

    # Подсчёт
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Пагинация
    query = query.offset(pagination.skip).limit(pagination.limit)
    result = await db.execute(query)
    tours = result.scalars().all()

    return PaginatedResponse.create(
        items=tours,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/my", response_model=PaginatedResponse[TourResponse])
async def get_my_tours(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить туры своей компании
    """

    # Находим компанию пользователя
    result = await db.execute(
        select(Company).filter(Company.owner_id == current_user.id)
    )
    company = result.scalars().first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У вас нет компании"
        )

    pagination = PaginationParams(page=page, per_page=per_page)

    # Запрос туров компании
    query = select(Tour).filter(Tour.company_id == company.id)
    count_query = select(func.count(Tour.id)).filter(Tour.company_id == company.id)

    # Подсчёт
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Пагинация
    query = query.offset(pagination.skip).limit(pagination.limit).order_by(Tour.id.desc())
    result = await db.execute(query)
    tours = result.scalars().all()

    return PaginatedResponse.create(
        items=tours,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{tour_id}", response_model=TourResponse)
async def get_tour(
        tour_id: int,
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить тур по ID
    """
    result = await db.execute(select(Tour).filter(Tour.id == tour_id))
    tour = result.scalars().first()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тур не найден"
        )

    return tour


@router.patch("/{tour_id}", response_model=TourResponse)
async def update_tour(
        tour_id: int,
        tour_update: TourUpdate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Обновить тур

    Только владелец компании или админ могут обновлять тур
    """
    result = await db.execute(
        select(Tour)
        .filter(Tour.id == tour_id)
    )
    tour = result.scalars().first()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тур не найден"
        )

    # Проверка прав
    result = await db.execute(select(Company).filter(Company.id == tour.company_id))
    company = result.scalars().first()

    if current_user.role != 'admin' and company.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для редактирования этого тура"
        )

    # Валидация цены
    if tour_update.price is not None and tour_update.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Цена должна быть больше нуля"
        )

    # Обновление
    update_data = tour_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tour, field, value)

    db.add(tour)
    await db.commit()
    await db.refresh(tour)

    return tour


@router.delete("/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tour(
        tour_id: int,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> None:
    """
    Удалить тур

    Только владелец компании или админ могут удалить тур
    """
    result = await db.execute(select(Tour).filter(Tour.id == tour_id))
    tour = result.scalars().first()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тур не найден"
        )

    # Проверка прав
    result = await db.execute(select(Company).filter(Company.id == tour.company_id))
    company = result.scalars().first()

    if current_user.role != 'admin' and company.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления этого тура"
        )

    await db.delete(tour)
    await db.commit()
