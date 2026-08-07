from fastapi import APIRouter

from app.services.geospatial.impact_service import compute_impact_area

router = APIRouter(
    prefix="/impact",
    tags=["Impact Assessment"],
)


@router.get("/estimate")
def estimate_impact(
    latitude: float,
    longitude: float,
    disaster_type: str,
    magnitude: float | None = None,
    alert_level: str | None = None,
):
    """
    Estimate the disaster impact area based on the
    supplied event parameters.
    """

    return compute_impact_area(
        latitude=latitude,
        longitude=longitude,
        disaster_type=disaster_type,
        magnitude=magnitude,
        alert_level=alert_level,
    )