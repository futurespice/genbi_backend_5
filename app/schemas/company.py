from pydantic import BaseModel


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
