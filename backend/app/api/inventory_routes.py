from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.resource_inventory import (
    ResourceInventoryCreate,
    ResourceInventoryResponse
)

from app.services.inventory_service import (
    create_inventory,
    get_all_inventory,
    get_inventory_by_id,
    update_inventory,
    delete_inventory
)

router = APIRouter(
    prefix="/inventory",
    tags=["Resource Inventory"]
)





@router.post("/", response_model=ResourceInventoryResponse)

def create_resource(
        inventory: ResourceInventoryCreate,
        db: Session = Depends(get_db)
):

    return create_inventory(db, inventory)


@router.get("/", response_model=list[ResourceInventoryResponse])

def get_resources(
        db: Session = Depends(get_db)
):

    return get_all_inventory(db)

@router.get("/{inventory_id}", response_model=ResourceInventoryResponse)

def get_resource_by_id(
    inventory_id: int,
    db: Session = Depends(get_db)
):

    inventory = get_inventory_by_id(db, inventory_id)

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Resource not found"
        )

    return inventory

@router.put("/{inventory_id}", response_model=ResourceInventoryResponse)
def update_resource(
    inventory_id: int,
    updated_inventory: ResourceInventoryCreate,
    db: Session = Depends(get_db)
):

    inventory = update_inventory(
        db,
        inventory_id,
        updated_inventory
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Resource not found"
        )

    return inventory

@router.delete("/{inventory_id}", response_model=ResourceInventoryResponse)
def delete_resource(
    inventory_id: int,
    db: Session = Depends(get_db)
):

    inventory = delete_inventory(
        db,
        inventory_id
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Resource not found"
        )

    return inventory