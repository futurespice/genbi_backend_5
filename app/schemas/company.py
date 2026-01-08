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
    owner_id: int | None = None  # ✅ ИСПРАВЛЕНО: может быть NULL если владелец удален

    class Config:
        from_attributes = True


# Компания с турами для аккордиона
class CompanyWithToursResponse(CompanyResponse):
    """
    Компания с турами для аккордиона
    """
    tours: List['TourResponse'] = []
    tours_count: int = 0


# Для избежания circular imports
from app.schemas.tour import TourResponse

CompanyWithToursResponse.model_rebuild()