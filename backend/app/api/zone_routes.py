from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.disaster_zone import DisasterZoneCreate, DisasterZoneListResponse, DisasterZoneResponse
from app.services.zone_service import (
    create_zone,
    delete_zone,
    get_zone_by_id,
    get_zones_near_depot,
    list_zones,
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


@router.get("/", response_model=DisasterZoneListResponse)

def get_zones(
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=5000),
        db: Session = Depends(get_db)
):
    total, records = list_zones(db, offset=offset, limit=limit)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "records": records,
    }


@router.get("/near-depot/{relief_center_id}", response_model=list[DisasterZoneResponse])
def get_zones_near_depot_endpoint(
    relief_center_id: int,
    radius_km: float = Query(default=50.0, gt=0, le=500),
    db: Session = Depends(get_db),
):
    zones = get_zones_near_depot(db, relief_center_id, radius_km)
    if zones is None:
        raise HTTPException(
            status_code=404,
            detail="Relief center not found",
        )
    return zones


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