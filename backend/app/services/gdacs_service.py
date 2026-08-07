from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config.settings import GDACS_URL
from app.services.ingestion.disaster_import_service import import_disaster


def get_gdacs_severity(alert_level: str | None) -> str:
    """
    Convert GDACS alert level into our internal severity.
    """

    if alert_level is None:
        return "Unknown"

    alert_level = alert_level.lower()

    if alert_level == "green":
        return "Low"

    elif alert_level == "orange":
        return "High"

    elif alert_level == "red":
        return "Critical"

    return "Unknown"


def fetch_gdacs_events(
    db: Session,
) -> dict:

    with httpx.Client(
        timeout=httpx.Timeout(
            connect=20.0,
            read=120.0,
            write=20.0,
            pool=20.0
        ),
        follow_redirects=True
    ) as client:

        response = client.get(GDACS_URL)

    response.raise_for_status()

    data = response.json()

    imported = 0

    skipped = 0

    for feature in data["features"]:

        properties = feature["properties"]

        geometry = feature["geometry"]

        coordinates = geometry["coordinates"]

        disaster = {

            "event_id": f'{properties["eventtype"]}-{properties["eventid"]}',

            "title": properties["description"],

            "disaster_type": properties["eventtype"],

            "magnitude": None,

            "latitude": coordinates[1],

            "longitude": coordinates[0],

            "location": properties["name"],

            "severity": get_gdacs_severity(
                properties.get("alertlevel")
            ),

            "source": "GDACS",

            "event_time": datetime.utcnow()

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