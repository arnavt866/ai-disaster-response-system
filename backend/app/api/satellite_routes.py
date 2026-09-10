from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.geospatial.satellite_service import (
    get_damage_estimation,
    get_nearby_facilities,
)

router = APIRouter(
    prefix="/satellite",
    tags=["OpenStreetMap"],
)


@router.get("/nearby")
def nearby_places(
    latitude: float,
    longitude: float,
    radius: int = 5000,
):
    return get_nearby_facilities(
        latitude,
        longitude,
        radius,
    )


@router.get("/damage")
def damage_estimation(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db),
):
    return get_damage_estimation(latitude, longitude, db=db)
