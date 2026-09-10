from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.ndma_service import fetch_ndma_events

router = APIRouter(
    prefix="/ndma",
    tags=["NDMA"],
)


@router.get("/")
def get_ndma_events(db: Session = Depends(get_db)):
    """Poll SACHET CAP alerts (early warning; not disaster impact)."""
    return fetch_ndma_events(db)
