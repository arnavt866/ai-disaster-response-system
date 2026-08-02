from datetime import datetime
from sqlalchemy.orm import Session

from app.models.disaster_event import DisasterEvent


def get_severity(magnitude: float | None) -> str:
    """
    Convert earthquake magnitude into severity level.
    """

    if magnitude is None:
        return "Unknown"

    if magnitude < 3:
        return "Low"

    elif magnitude < 5:
        return "Moderate"

    elif magnitude < 7:
        return "High"

    return "Critical"


def disaster_exists(
    db: Session,
    event_id: str
) -> bool:
    """
    Check whether an event already exists.
    """

    return (
        db.query(DisasterEvent)
        .filter(DisasterEvent.event_id == event_id)
        .first()
        is not None
    )


def import_disaster(
    db: Session,
    disaster_data: dict
):
    """
    Import a single disaster into PostgreSQL.
    """

    if disaster_exists(db, disaster_data["event_id"]):
        return None

    disaster = DisasterEvent(

        event_id=disaster_data["event_id"],

        title=disaster_data["title"],

        disaster_type=disaster_data["disaster_type"],

        magnitude=disaster_data["magnitude"],

        latitude=disaster_data["latitude"],

        longitude=disaster_data["longitude"],

        location=disaster_data["location"],

        severity=disaster_data["severity"],

        status="Active",

        source=disaster_data["source"],

        event_time=disaster_data["event_time"]
        or datetime.utcnow()

    )

    db.add(disaster)

    return disaster