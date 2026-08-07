from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.ingestion.building_import_service import import_buildings

router = APIRouter(
    prefix="/buildings",
    tags=["Buildings"],
)


@router.post("/import")
def import_all_buildings(
    force: bool = False,
    confirm: bool = False,
    db: Session = Depends(get_db),
):
    """
    Import buildings from the local OSM dataset.

    The import is skipped if buildings already exist.
    Set `force=true` to run the import again.
    """
    if force and not confirm:

        return {

            "status": "Confirmation Required",

            "message": (
                "This will scan the entire India OSM dataset again. "
                "Use confirm=true if you really want to re-import."
            )

        }

    start = datetime.now()

    try:
        result = import_buildings(
            db=db,
            force=force,
        )

        result["time_taken"] = str(datetime.now() - start)
        result["status"] = "SUCCESS"

        return result

    except Exception as e:

        db.rollback()

        return {
            "status": "FAILED",
            "error": str(e),
        }