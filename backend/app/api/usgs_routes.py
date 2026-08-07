import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.usgs_service import fetch_usgs_earthquakes

router = APIRouter(
    prefix="/usgs",
    tags=["USGS Earthquake API"]
)


@router.get("/import")
def import_usgs_data(
    db: Session = Depends(get_db)
):
    """
    Fetch latest earthquakes from USGS
    and store them in PostgreSQL.
    """

    try:

        result = fetch_usgs_earthquakes(db)

        return {

            "message": "USGS earthquake import completed successfully.",

            "summary": result
        }

    except httpx.HTTPError as e:

        raise HTTPException(

            status_code=503,

            detail=f"Unable to connect to USGS API: {str(e)}"

        )

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=f"Unexpected Error: {str(e)}"

        )