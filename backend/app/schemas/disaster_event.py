from datetime import datetime

from pydantic import BaseModel, Field


class DisasterEventBase(BaseModel):

    event_id: str

    title: str

    disaster_type: str

    magnitude: float | None = None

    latitude: float = Field(ge=-90, le=90)

    longitude: float = Field(ge=-180, le=180)

    location: str | None = None

    severity: str | None = None

    status: str = "Active"

    source: str | None = None

    event_time: datetime | None = None


class DisasterEventCreate(DisasterEventBase):
    pass


class DisasterEventResponse(DisasterEventBase):

    id: int

    class Config:

        from_attributes = True


class DisasterEventListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    records: list[DisasterEventResponse]