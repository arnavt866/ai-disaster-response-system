from pydantic import BaseModel, Field


class PriorityOverrideRequest(BaseModel):
    priority: str = Field(..., pattern="^(Critical|High|Moderate|Low)$")


class AllocationRunRequest(BaseModel):
    zone_ids: list[int] | None = None
    persist: bool = True
    confirm_all_zones: bool = False
    max_zones: int | None = Field(default=None, description="Optional sanity cap on number of zones for full-system runs")


class RouteRequest(BaseModel):
    relief_center_id: int
    zone_id: int
    blocked: bool = False


class RoadBlockRequest(BaseModel):
    region_id: str
    u: int | str
    v: int | str


class RoadBlockClearRequest(BaseModel):
    region_id: str | None = None
