from pydantic import BaseModel, Field


class ResourceInventoryBase(BaseModel):
    resource_name: str
    category: str
    quantity: int = Field(ge=0)
    reserved_quantity: int = Field(0, ge=0)
    in_transit_quantity: int = Field(0, ge=0)
    unit: str
    warehouse: str
    status: str


class ResourceInventoryCreate(ResourceInventoryBase):
    pass


class ResourceInventoryResponse(ResourceInventoryBase):
    id: int

    class Config:
        from_attributes = True