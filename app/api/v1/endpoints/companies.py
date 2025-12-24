from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from app.api import deps
from app.db.session import get_db
from app.models.company import Company
from app.models.tour import Tour
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate, CompanyWithToursResponse
from app.schemas.pagination import PaginatedResponse, PaginationParams

router = APIRouter()


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
        company_in: CompanyCreate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Создать новую компанию

    ⚠️ ВАЖНО: Этот эндпоинт НЕ ДОЛЖЕН использоваться напрямую!
    Компании создаются автоматически при одобрении заявки через /applications

    Только пользователи с ролью COMPANY или ADMIN могут создавать компании
    """

    # Проверка уникальности названия
    result = await db.execute(select(Company).filter(Company.name == company_in.name))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Компания с таким названием уже существует"
        )

    # Проверка: у пользователя не должно быть компании
    if current_user.role == 'company':
        result = await db.execute(
            select(Company).filter(Company.owner_id == current_user.id)
        )
        existing_company = result.scalars().first()
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"У вас уже есть компания: {existing_company.name}"
            )

    # Создание компании
    company = Company(
        **company_in.model_dump(),
        owner_id=current_user.id
    )

    db.add(company)
    await db.commit()
    await db.refresh(company)

    return company


@router.get("/", response_model=PaginatedResponse[CompanyWithToursResponse])
async def get_companies(
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(20, ge=1, le=100, description="Элементов на странице"),
        search: str | None = Query(None, description="Поиск по названию"),
        include_tours: bool = Query(False, description="Включить туры в ответ (для аккордиона)"),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить список компаний с пагинацией

    ✅ НОВОЕ: Поддержка аккордиона с турами

    Параметры:
    - page: Номер страницы
    - per_page: Количество элементов на странице
    - search: Поиск по названию
    - include_tours: Включить туры в ответ (для аккордиона)

    Примеры использования:
    1. Базовый список: GET /companies
    2. С турами (аккордион): GET /companies?include_tours=true
    3. Поиск с турами: GET /companies?search=Adventure&include_tours=true
    """

    pagination = PaginationParams(page=page, per_page=per_page)

    # Базовый запрос
    query = select(Company)
    count_query = select(func.count(Company.id))

    # Если нужны туры - добавляем eager loading
    if include_tours:
        query = query.options(selectinload(Company.tours))

    # Поиск
    if search:
        search_filter = Company.name.ilike(f"%{search}%")
        query = query.filter(search_filter)
        count_query = count_query.filter(search_filter)

    # Подсчёт
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Пагинация
    query = query.offset(pagination.skip).limit(pagination.limit)
    result = await db.execute(query)
    companies = result.scalars().all()

    # Формируем ответ
    if include_tours:
        # С турами для аккордиона
        items = []
        for company in companies:
            # Подсчитываем активные туры
            active_tours = [tour for tour in company.tours if tour.is_active]
            items.append({
                "id": company.id,
                "name": company.name,
                "address": company.address,
                "work_hours": company.work_hours,
                "website": company.website,
                "owner_id": company.owner_id,
                "tours": active_tours,
                "tours_count": len(active_tours)
            })
    else:
        # Без туров (базовый список)
        items = companies

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/my", response_model=CompanyWithToursResponse)
async def get_my_company(
        include_tours: bool = Query(True, description="Включить туры"),
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить свою компанию

    По умолчанию включает туры (include_tours=true)
    """
    query = select(Company).filter(Company.owner_id == current_user.id)

    if include_tours:
        query = query.options(selectinload(Company.tours))

    result = await db.execute(query)
    company = result.scalars().first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У вас нет компании"
        )

    # Формируем ответ с турами
    if include_tours:
        active_tours = [tour for tour in company.tours if tour.is_active]
        return {
            "id": company.id,
            "name": company.name,
            "address": company.address,
            "work_hours": company.work_hours,
            "website": company.website,
            "owner_id": company.owner_id,
            "tours": active_tours,
            "tours_count": len(active_tours)
        }

    return company


@router.get("/{company_id}", response_model=CompanyWithToursResponse)
async def get_company(
        company_id: int,
        include_tours: bool = Query(True, description="Включить туры"),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить компанию по ID

    По умолчанию включает туры (include_tours=true)
    """
    query = select(Company).filter(Company.id == company_id)

    if include_tours:
        query = query.options(selectinload(Company.tours))

    result = await db.execute(query)
    company = result.scalars().first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )

    # Формируем ответ с турами
    if include_tours:
        active_tours = [tour for tour in company.tours if tour.is_active]
        return {
            "id": company.id,
            "name": company.name,
            "address": company.address,
            "work_hours": company.work_hours,
            "website": company.website,
            "owner_id": company.owner_id,
            "tours": active_tours,
            "tours_count": len(active_tours)
        }

    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
        company_id: int,
        company_update: CompanyUpdate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Обновить компанию

    Только владелец или админ могут обновлять компанию
    """
    result = await db.execute(select(Company).filter(Company.id == company_id))
    company = result.scalars().first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )

    # Проверка прав
    if current_user.role != 'admin' and company.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для редактирования этой компании"
        )

    # Проверка уникальности названия
    if company_update.name:
        result = await db.execute(
            select(Company).filter(
                Company.name == company_update.name,
                Company.id != company_id
            )
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Компания с таким названием уже существует"
            )

    # Обновление
    update_data = company_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    db.add(company)
    await db.commit()
    await db.refresh(company)

    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
        company_id: int,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> None:
    """
    Удалить компанию

    Только владелец или админ могут удалить компанию
    """
    result = await db.execute(select(Company).filter(Company.id == company_id))
    company = result.scalars().first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )

    # Проверка прав
    if current_user.role != 'admin' and company.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления этой компании"
        )

    await db.delete(company)
    await db.commit()