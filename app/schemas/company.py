from pydantic import BaseModel
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.tour import TourResponse


class CompanyBase(BaseModel):
    name: str
    address: str | None = None
    work_hours: str | None = None
    website: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    work_hours: str | None = None
    website: str | None = None


class CompanyResponse(CompanyBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True


# ✅ НОВОЕ: Компания с турами для аккордиона
class CompanyWithToursResponse(CompanyResponse):
    """
    Компания с турами для аккордиона

    При GET /companies можно запросить с параметром ?include_tours=true
    Тогда будет возвращаться список туров компании

    Использование на фронтенде:
    - При загрузке списка компаний получаем только базовую информацию
    - При клике на компанию (раскрытие аккордиона) подгружаем туры
    - Или сразу загружаем все с include_tours=true
    """
    tours: List['TourResponse'] = []
    tours_count: int = 0  # Количество туров для badge


# Для избежания circular imports
from app.schemas.tour import TourResponse

CompanyWithToursResponse.model_rebuild()