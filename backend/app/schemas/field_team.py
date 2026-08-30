from datetime import datetime

from pydantic import BaseModel, Field


class FieldTeamCreate(BaseModel):
    team_name: str
    vehicle_type: str | None = None
    vehicle_capacity: int = Field(0, ge=0)
    contact_number: str | None = None
    base_latitude: float | None = Field(None, ge=-90, le=90)
    base_longitude: float | None = Field(None, ge=-180, le=180)


class FieldTeamResponse(FieldTeamCreate):
    id: int
    status: str

    class Config:
        from_attributes = True


class FieldTeamStatusUpdate(BaseModel):
    status: str
