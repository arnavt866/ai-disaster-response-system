from sqlalchemy.orm import Session
from datetime import datetime
from app.models.disaster_zone import DisasterZone


def create_disaster_zones(
    db: Session,
    disaster_type: str,
    analyzed_cells: list[dict],
) -> int:
    """
    Save every analyzed grid into PostgreSQL
    using one bulk insert.
    """

    zones = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    for index, cell in enumerate(analyzed_cells, start=1):

        geometry = cell["geometry"]

        centroid = geometry["coordinates"][0][0]

        zone = DisasterZone(

            zone_name=f"{disaster_type.upper()}-{timestamp}-Zone-{index}",

            disaster_type=disaster_type,

            severity=cell["severity_level"],

            latitude=centroid[1],

            longitude=centroid[0],

            affected_population=cell["estimated_population"],

            status="Active",

        )

        zones.append(zone)

    db.bulk_save_objects(zones)

    db.commit()

    return len(zones)