import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import USGS_URL
from app.services.disaster_import_service import import_disaster

def get_usgs_severity(
    magnitude: float | None
) -> str:

    if magnitude is None:
        return "Unknown"

    if magnitude < 3:
        return "Low"

    elif magnitude < 5:
        return "Moderate"

    elif magnitude < 7:
        return "High"

    return "Critical"

def fetch_usgs_earthquakes(db: Session):
    """
    Fetch earthquake data from the USGS feed
    and import new events into the database.
    """

    response = httpx.get(
        USGS_URL,
        timeout=30.0
    )

    response.raise_for_status()

    data = response.json()

    imported = 0
    skipped = 0

    for feature in data["features"]:

        properties = feature["properties"]

        geometry = feature["geometry"]

        coordinates = geometry["coordinates"]

        disaster = {

            "event_id": feature["id"],

            "title": properties["title"],

            "disaster_type": "Earthquake",

            "magnitude": properties["mag"],

            "latitude": coordinates[1],

            "longitude": coordinates[0],

            "location": properties["place"],

            "source": "USGS",

            "severity": get_usgs_severity(
                properties["mag"]
            ),

            "event_time": datetime.fromtimestamp(
                properties["time"] / 1000
            )
        }

        result = import_disaster(
            db,
            disaster
        )

        if result:

            imported += 1

        else:

            skipped += 1

    db.commit()

    return {

        "total": len(data["features"]),

        "imported": imported,

        "skipped": skipped
    }