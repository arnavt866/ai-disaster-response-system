from pydantic import BaseModel, Field


class PriorityOverrideRequest(BaseModel):
    priority: str = Field(..., pattern="^(Critical|High|Moderate|Low)$")


class AllocationRunRequest(BaseModel):
    zone_ids: list[int] | None = None
    persist: bool = True


class RouteRequest(BaseModel):
    relief_center_id: int
    zone_id: int
    blocked: bool = False
