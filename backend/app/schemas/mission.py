from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MissionCreate(BaseModel):
    zone_id: int
    field_team_id: int | None = None
    relief_center_id: int | None = None
    priority: str = "Moderate"
    resources_payload: dict[str, Any] | None = None


class MissionStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(Created|Allocated|Dispatched|In Transit|Delivered)$",
    )


class MissionTeamAssign(BaseModel):
    field_team_id: int = Field(..., ge=1)


class MissionResponse(BaseModel):
    id: int
    mission_code: str
    zone_id: int
    field_team_id: int | None
    relief_center_id: int | None
    priority: str
    status: str
    route_distance_km: float | None
    route_eta_hours: float | None
    route_status: str
    resources_payload: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
