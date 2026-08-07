from pydantic import BaseModel


class BuildingCreate(BaseModel):
    osm_id: int
    latitude: float
    longitude: float


class BuildingResponse(BuildingCreate):
    id: int

    class Config:
        from_attributes = True