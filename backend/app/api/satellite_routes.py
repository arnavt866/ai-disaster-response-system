from fastapi import APIRouter

from app.services.satellite_service import (
    get_nearby_facilities
)

router = APIRouter(
    prefix="/satellite",
    tags=["OpenStreetMap"]
)


@router.get("/nearby")
def nearby_places(
    latitude: float,
    longitude: float,
    radius: int = 5000
):

    return get_nearby_facilities(
        latitude,
        longitude,
        radius
    )