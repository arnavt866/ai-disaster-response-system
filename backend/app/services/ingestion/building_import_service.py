from sqlalchemy.orm import Session

from app.config.settings import BUILDING_IMPORT_BATCH_SIZE
from app.core.logger import logger
from app.models.building import Building
from app.services.ingestion.osm_reader import (
    BuildingStreamHandler,
    OSM_FILE,
)


def import_buildings(
    db: Session,
    force: bool = False,
) -> dict:

    # -----------------------------------------
    # Skip import if buildings already exist
    # -----------------------------------------

    existing_count = db.query(Building).count()

    if existing_count > 0 and not force:

        logger.info(

            "Buildings already imported. Skipping import."

        )

        return {

            "message": "Buildings already exist.",

            "building_count": existing_count,

            "imported": 0,

            "skipped": existing_count,

            "total_processed": existing_count,

        }

    imported = 0
    skipped = 0

    logger.info("=" * 60)
    logger.info("Starting OSM Building Import")
    logger.info("=" * 60)
    # Save one batch of streamed buildings.
    def save_batch(batch):

        nonlocal imported
        nonlocal skipped

        osm_ids = [

            b["osm_id"]

            for b in batch

        ]

        existing = (

            db.query(Building.osm_id)

            .filter(

                Building.osm_id.in_(osm_ids)

            )

            .all()

        )

        existing_ids = {row[0] for row in existing}

        new_rows = []

        for building in batch:

            if building["osm_id"] in existing_ids:

                skipped += 1

                continue

            new_rows.append(

                Building(

                    osm_id=building["osm_id"],

                    latitude=building["latitude"],

                    longitude=building["longitude"],

                )

            )

        if new_rows:

            db.bulk_save_objects(new_rows)

            db.commit()

            imported += len(new_rows)

            logger.info(

                f"Imported : {imported:,}    "

                f"Skipped : {skipped:,}"

            )

    handler = BuildingStreamHandler(

        callback=save_batch,

        batch_size=BUILDING_IMPORT_BATCH_SIZE,

    )

    handler.apply_file(

        str(OSM_FILE),

        locations=True,

    )

    handler.finish()

    logger.info("=" * 60)
    logger.info("IMPORT FINISHED")
    logger.info("=" * 60)

    return {

        "imported": imported,

        "skipped": skipped,

        "total_processed": handler.total,

    }