from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.disaster_event import (
    DisasterEventCreate,
    DisasterEventListResponse,
    DisasterEventResponse,
)
from app.services.disaster_service import (
    create_disaster,
    delete_disaster,
    get_disaster_by_id,
    list_disasters,
    update_disaster,
)
from app.services.advisory_service import get_disaster_zone_advisory

router = APIRouter(
    prefix="/disasters",
    tags=["Disaster Events"],
)


@router.post("/", response_model=DisasterEventResponse)
def create_disaster_event(
    disaster: DisasterEventCreate,
    db: Session = Depends(get_db),
):
    """Create a new disaster event."""

    return create_disaster(db, disaster)


@router.get("/", response_model=DisasterEventListResponse)
def get_disasters(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """Return disaster events with offset/limit pagination."""

    total, records = list_disasters(db, offset=offset, limit=limit)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "records": records,
    }


@router.get("/{disaster_id}", response_model=DisasterEventResponse)
def get_disaster(
    disaster_id: int,
    db: Session = Depends(get_db),
):
    """Return a disaster event by ID."""

    disaster = get_disaster_by_id(
        db,
        disaster_id,
    )

    if disaster is None:
        raise HTTPException(
            status_code=404,
            detail="Disaster Event not found",
        )

    return disaster


@router.get("/{disaster_id}/zone-advisory")
def disaster_zone_advisory(
    disaster_id: int,
    radius_km: float = Query(150.0, ge=1.0, le=500.0),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Read-only rule-based advisory scores for active zones near a disaster event."""
    try:
        return get_disaster_zone_advisory(
            db,
            disaster_id,
            radius_km=radius_km,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{disaster_id}", response_model=DisasterEventResponse)
def update_disaster_event(
    disaster_id: int,
    updated_disaster: DisasterEventCreate,
    db: Session = Depends(get_db),
):
    """Update an existing disaster event."""

    disaster = update_disaster(
        db,
        disaster_id,
        updated_disaster,
    )

    if disaster is None:
        raise HTTPException(
            status_code=404,
            detail="Disaster Event not found",
        )

    return disaster


@router.delete("/{disaster_id}", response_model=DisasterEventResponse)
def delete_disaster_event(
    disaster_id: int,
    db: Session = Depends(get_db),
):
    """Delete a disaster event."""

    disaster = delete_disaster(
        db,
        disaster_id,
    )

    if disaster is None:
        raise HTTPException(
            status_code=404,
            detail="Disaster Event not found",
        )

    return disaster