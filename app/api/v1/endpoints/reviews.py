from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_

from app.api import deps
from app.db.session import get_db
from app.models.review import Review
from app.models.tour import Tour
from app.models.company import Company
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse
from app.schemas.pagination import PaginatedResponse, PaginationParams

router = APIRouter()


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
        review_in: ReviewCreate,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Создать отзыв

    - **target_type**: Тип объекта (tour/company)
    - **target_id**: ID объекта
    - **rating**: Оценка от 1 до 5
    - **comment**: Текст отзыва
    """

    # Валидация рейтинга
    if review_in.rating < 1 or review_in.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Рейтинг должен быть от 1 до 5"
        )

    # Валидация target_id и проверка дубликата
    if review_in.target_type == 'tour':
        # Проверка существования тура
        res = await db.execute(select(Tour).filter(Tour.id == review_in.target_id))
        tour = res.scalars().first()
        if not tour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тур не найден"
            )

        # Проверка дублирования отзыва
        res = await db.execute(
            select(Review).filter(
                and_(
                    Review.author_id == current_user.id,
                    Review.tour_id == review_in.target_id
                )
            )
        )
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы уже оставили отзыв на этот тур"
            )

        # Создаём отзыв
        review = Review(
            author_id=current_user.id,
            target_type=review_in.target_type,
            tour_id=review_in.target_id,
            company_id=None,
            rating=review_in.rating,
            comment=review_in.comment
        )

    elif review_in.target_type == 'company':
        # Проверка существования компании
        res = await db.execute(select(Company).filter(Company.id == review_in.target_id))
        company = res.scalars().first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Компания не найдена"
            )

        # Проверка дублирования отзыва
        res = await db.execute(
            select(Review).filter(
                and_(
                    Review.author_id == current_user.id,
                    Review.company_id == review_in.target_id
                )
            )
        )
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы уже оставили отзыв на эту компанию"
            )

        # Создаём отзыв
        review = Review(
            author_id=current_user.id,
            target_type=review_in.target_type,
            tour_id=None,
            company_id=review_in.target_id,
            rating=review_in.rating,
            comment=review_in.comment
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type должен быть 'tour' или 'company'"
        )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    # Пересчитываем средний рейтинг
    await _update_rating(db, review_in.target_type, review_in.target_id)

    return review


@router.get("/", response_model=PaginatedResponse[ReviewResponse])
async def get_reviews(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        target_type: str | None = Query(None, description="Фильтр по типу (tour/company)"),
        target_id: int | None = Query(None, description="ID объекта"),
        is_moderated: bool | None = Query(None, description="Фильтр по модерации"),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить список отзывов

    - **page**: Номер страницы
    - **per_page**: Количество элементов на странице
    - **target_type**: Фильтр по типу (tour/company)
    - **target_id**: ID объекта
    - **is_moderated**: Фильтр по модерации
    """

    pagination = PaginationParams(page=page, per_page=per_page)

    query = select(Review)
    count_query = select(func.count(Review.id))

    # Фильтры
    if target_type:
        query = query.filter(Review.target_type == target_type)
        count_query = count_query.filter(Review.target_type == target_type)

    if target_id is not None:
        if target_type == 'tour':
            query = query.filter(Review.tour_id == target_id)
            count_query = count_query.filter(Review.tour_id == target_id)
        elif target_type == 'company':
            query = query.filter(Review.company_id == target_id)
            count_query = count_query.filter(Review.company_id == target_id)

    if is_moderated is not None:
        query = query.filter(Review.is_moderated == is_moderated)
        count_query = count_query.filter(Review.is_moderated == is_moderated)

    # Подсчёт
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Пагинация
    query = query.offset(pagination.skip).limit(pagination.limit).order_by(Review.created_at.desc())
    result = await db.execute(query)
    reviews = result.scalars().all()

    return PaginatedResponse.create(
        items=reviews,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
        review_id: int,
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получить отзыв по ID
    """
    result = await db.execute(select(Review).filter(Review.id == review_id))
    review = result.scalars().first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    return review


@router.patch("/{review_id}/moderate", response_model=ReviewResponse)
async def moderate_review(
        review_id: int,
        current_user: User = Depends(deps.get_current_admin),
        db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Модерировать отзыв (только админ)
    """
    result = await db.execute(select(Review).filter(Review.id == review_id))
    review = result.scalars().first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    review.is_moderated = True
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return review


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
        review_id: int,
        current_user: User = Depends(deps.get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> None:
    """
    Удалить отзыв

    - Админ может удалить любой отзыв
    - Пользователь может удалить только свой отзыв
    """
    result = await db.execute(select(Review).filter(Review.id == review_id))
    review = result.scalars().first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    # Проверка прав
    if current_user.role != 'admin' and review.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления этого отзыва"
        )

    # Сохраняем данные для пересчёта рейтинга
    target_type = review.target_type
    target_id = review.tour_id if target_type == 'tour' else review.company_id

    await db.delete(review)
    await db.commit()

    # Пересчитываем рейтинг после удаления
    if target_id:
        await _update_rating(db, target_type, target_id)


async def _update_rating(db: AsyncSession, target_type: str, target_id: int):
    """
    Пересчитать средний рейтинг для тура или компании
    """
    if target_type == 'tour':
        # Вычисляем средний рейтинг для тура
        result = await db.execute(
            select(func.avg(Review.rating)).filter(Review.tour_id == target_id)
        )
        avg_rating = result.scalar() or 0.0

        # Обновляем тур
        tour_result = await db.execute(select(Tour).filter(Tour.id == target_id))
        tour = tour_result.scalars().first()
        if tour:
            tour.rating = round(avg_rating, 2)
            db.add(tour)
            await db.commit()

    # Для компаний пока не храним рейтинг, но можно добавить аналогично