from datetime import datetime

from pydantic import BaseModel, Field


class DisasterZoneBase(BaseModel):
    zone_name: str
    disaster_type: str
    severity: str
    latitude: float = Field(ge=-90, le=90)

    longitude: float = Field(ge=-180, le=180)

    affected_population: int = Field(ge=0)
    status: str = "Active"
    operational_priority: str = "Moderate"


class DisasterZoneCreate(DisasterZoneBase):
    pass


class DisasterZoneResponse(DisasterZoneBase):
    id: int
    elderly_share: float | None = None
    child_share: float | None = None
    vulnerability_data_available: bool = False
    vulnerability_source: str | None = None
    vulnerability_computed_at: datetime | None = None

    class Config:
        from_attributes = True


class DisasterZoneListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    records: list[DisasterZoneResponse]