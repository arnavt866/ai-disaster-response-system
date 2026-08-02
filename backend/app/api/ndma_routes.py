from fastapi import APIRouter

from app.services.ndma_service import fetch_ndma_events

router = APIRouter(
    prefix="/ndma",
    tags=["NDMA"]
)


@router.get("/")
def get_ndma_events():

    return fetch_ndma_events()