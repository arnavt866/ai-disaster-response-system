from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db

from app.services.gdacs_service import fetch_gdacs_events

router = APIRouter(
    prefix="/gdacs",
    tags=["GDACS"]
)


@router.get("/import")
def import_gdacs(
    db: Session = Depends(get_db)
):
    """
    Import live disasters from GDACS.
    """

    result = fetch_gdacs_events(db)

    return {
        "message": "GDACS import completed successfully.",
        "summary": result
    }