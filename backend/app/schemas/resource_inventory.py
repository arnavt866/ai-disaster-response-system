from pydantic import BaseModel, Field


class ResourceInventoryBase(BaseModel):
    resource_name: str
    category: str
    quantity: int = Field(gt=0)
    unit: str
    warehouse: str
    status: str


class ResourceInventoryCreate(ResourceInventoryBase):
    pass


class ResourceInventoryResponse(ResourceInventoryBase):
    id: int

    class Config:
        from_attributes = True