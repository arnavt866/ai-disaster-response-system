from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.disaster_zone import DisasterZoneCreate, DisasterZoneResponse
from app.services.zone_service import (
    create_zone,
    delete_zone,
    get_all_zones,
    get_zone_by_id,
    update_zone,
)

router = APIRouter(
    prefix="/zones",
    tags=["Disaster Zones"]
)





@router.post("/", response_model=DisasterZoneResponse)

def create_disaster_zone(
        zone: DisasterZoneCreate,
        db: Session = Depends(get_db)
):

    return create_zone(db, zone)


@router.get("/", response_model=list[DisasterZoneResponse])

def get_zones(
        db: Session = Depends(get_db)
):

    return get_all_zones(db)

@router.get("/{zone_id}", response_model=DisasterZoneResponse)
def get_zone(
    zone_id: int,
    db: Session = Depends(get_db)
):

    zone = get_zone_by_id(
        db,
        zone_id
    )

    if zone is None:

        raise HTTPException(
            status_code=404,
            detail="Disaster Zone not found"
        )

    return zone

@router.put("/{zone_id}", response_model=DisasterZoneResponse)
def update_disaster_zone(
    zone_id: int,
    updated_zone: DisasterZoneCreate,
    db: Session = Depends(get_db)
):

    zone = update_zone(
        db,
        zone_id,
        updated_zone
    )

    if zone is None:

        raise HTTPException(
            status_code=404,
            detail="Disaster Zone not found"
        )

    return zone

@router.delete("/{zone_id}", response_model=DisasterZoneResponse)
def delete_disaster_zone(
    zone_id: int,
    db: Session = Depends(get_db)
):

    zone = delete_zone(
        db,
        zone_id
    )

    if zone is None:

        raise HTTPException(
            status_code=404,
            detail="Disaster Zone not found"
        )

    return zone