from pydantic import BaseModel, Field


class ReliefCenterBase(BaseModel):
    name: str
    address: str
    latitude: float = Field(ge=-90, le=90)

    longitude: float = Field(ge=-180, le=180)

    capacity: int = Field(gt=0)

    available_capacity: int = Field(ge=0)
    contact_number: str | None = None
    status: str = "Active"


class ReliefCenterCreate(ReliefCenterBase):
    pass


class ReliefCenterResponse(ReliefCenterBase):
    id: int

    class Config:
        from_attributes = True