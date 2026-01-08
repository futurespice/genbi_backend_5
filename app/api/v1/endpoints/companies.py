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

    ✅ ИСПРАВЛЕНО: N+1 problem устранен через eager loading
    """

    pagination = PaginationParams(page=page, per_page=per_page)

    # Базовый запрос
    query = select(Company)
    count_query = select(func.count(Company.id))

    # ✅ КРИТИЧНО: Eager loading туров ТОЛЬКО если запрошено
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

    # ✅ ИСПРАВЛЕНО: Формируем ответ БЕЗ доступа к lazy loaded атрибутам
    if include_tours:
        items = []
        for company in companies:
            # Фильтруем активные туры В ПАМЯТИ (туры уже загружены через selectinload)
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
        # ✅ Без туров - просто возвращаем компании
        items = [
            {
                "id": c.id,
                "name": c.name,
                "address": c.address,
                "work_hours": c.work_hours,
                "website": c.website,
                "owner_id": c.owner_id,
                "tours": [],
                "tours_count": 0
            }
            for c in companies
        ]

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

    ✅ ИСПРАВЛЕНО: Eager loading для избежания N+1
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

    return {
        "id": company.id,
        "name": company.name,
        "address": company.address,
        "work_hours": company.work_hours,
        "website": company.website,
        "owner_id": company.owner_id,
        "tours": [],
        "tours_count": 0
    }


@router.get("/{company_id}", response_model=CompanyWithToursResponse)
async def get_company(
        company_id: int,
        include_tours: bool = Query(True, description="Включить туры"),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить компанию по ID

    ✅ ИСПРАВЛЕНО: Eager loading для избежания N+1
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

    return {
        "id": company.id,
        "name": company.name,
        "address": company.address,
        "work_hours": company.work_hours,
        "website": company.website,
        "owner_id": company.owner_id,
        "tours": [],
        "tours_count": 0
    }


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
        company_id: int,
        company_update: CompanyUpdate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Обновить компанию
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