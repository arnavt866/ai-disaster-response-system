from sqlalchemy.orm import Session

from app.models.resource_inventory import ResourceInventory
from app.schemas.resource_inventory import ResourceInventoryCreate


def create_inventory(db: Session, inventory: ResourceInventoryCreate):

    db_inventory = ResourceInventory(**inventory.model_dump())

    db.add(db_inventory)

    db.commit()

    db.refresh(db_inventory)

    return db_inventory


def get_all_inventory(db: Session):

    return db.query(ResourceInventory).all()

def get_inventory_by_id(db: Session, inventory_id: int):

    return (
        db.query(ResourceInventory)
        .filter(ResourceInventory.id == inventory_id)
        .first()
    )

def update_inventory(
    db: Session,
    inventory_id: int,
    updated_inventory: ResourceInventoryCreate
):

    inventory = (
        db.query(ResourceInventory)
        .filter(ResourceInventory.id == inventory_id)
        .first()
    )

    if inventory is None:
        return None

    inventory.resource_name = updated_inventory.resource_name
    inventory.category = updated_inventory.category
    inventory.quantity = updated_inventory.quantity
    inventory.unit = updated_inventory.unit
    inventory.warehouse = updated_inventory.warehouse
    inventory.status = updated_inventory.status

    db.commit()

    db.refresh(inventory)

    return inventory

def delete_inventory(
    db: Session,
    inventory_id: int
):

    inventory = (
        db.query(ResourceInventory)
        .filter(ResourceInventory.id == inventory_id)
        .first()
    )

    if inventory is None:
        return None

    db.delete(inventory)

    db.commit()

    return inventory