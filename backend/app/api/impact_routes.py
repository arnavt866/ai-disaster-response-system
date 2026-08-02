from fastapi import APIRouter

from app.services.impact_service import assess_disaster_impact

router = APIRouter(
    prefix="/impact",
    tags=["Impact Assessment"]
)


@router.post("/assess")
def assess_impact(disaster: dict):

    return assess_disaster_impact(disaster)