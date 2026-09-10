from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.models.disaster_zone import DisasterZone
from app.schemas.disaster_zone import DisasterZoneCreate
from app.services.geospatial.zone_geometry import point_from_lat_lon
from app.services.relief_service import get_relief_center_by_id


def create_zone(db: Session, zone: DisasterZoneCreate) -> DisasterZone:

    db_zone = DisasterZone(**zone.model_dump())
    db_zone.location = point_from_lat_lon(zone.latitude, zone.longitude)

    db.add(db_zone)

    db.commit()

    db.refresh(db_zone)

    return db_zone


def get_all_zones(db: Session) -> list[DisasterZone]:

    return db.query(DisasterZone).order_by(DisasterZone.id.asc()).all()


def list_zones(
    db: Session,
    *,
    offset: int,
    limit: int,
) -> tuple[int, list[DisasterZone]]:
    query = db.query(DisasterZone)
    total = query.count()
    rows = (
        query.order_by(DisasterZone.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, rows

def get_zone_by_id(
    db: Session,
    zone_id: int
) -> DisasterZone | None:

    return (
        db.query(DisasterZone)
        .filter(DisasterZone.id == zone_id)
        .first()
    )

def update_zone(
    db: Session,
    zone_id: int,
    updated_zone: DisasterZoneCreate
) -> DisasterZone | None:

    zone = (
        db.query(DisasterZone)
        .filter(DisasterZone.id == zone_id)
        .first()
    )

    if zone is None:
        return None

    zone.zone_name = updated_zone.zone_name
    zone.disaster_type = updated_zone.disaster_type
    zone.severity = updated_zone.severity
    zone.latitude = updated_zone.latitude
    zone.longitude = updated_zone.longitude
    zone.location = point_from_lat_lon(
        updated_zone.latitude,
        updated_zone.longitude,
    )
    zone.affected_population = updated_zone.affected_population
    zone.status = updated_zone.status
    zone.operational_priority = updated_zone.operational_priority

    db.commit()

    db.refresh(zone)

    return zone

def delete_zone(
    db: Session,
    zone_id: int
) -> DisasterZone | None:

    zone = (
        db.query(DisasterZone)
        .filter(DisasterZone.id == zone_id)
        .first()
    )

    if zone is None:
        return None

    db.delete(zone)

    db.commit()

    return zone


def get_zones_near_depot(
    db: Session,
    relief_center_id: int,
    radius_km: float,
) -> list[DisasterZone] | None:
    """
    Return disaster zones within radius_km of a relief center depot.

    Uses PostGIS ST_DWithin on geography casts for meter-accurate distance.
    Optional capability — does not affect existing allocation logic.
    """
    depot = get_relief_center_by_id(db, relief_center_id)
    if depot is None:
        return None

    radius_m = radius_km * 1000.0
    depot_point = func.ST_SetSRID(
        func.ST_MakePoint(depot.longitude, depot.latitude),
        4326,
    )
    depot_geography = cast(depot_point, Geography)
    zone_geography = cast(DisasterZone.location, Geography)

    return (
        db.query(DisasterZone)
        .filter(DisasterZone.status == "Active")
        .filter(DisasterZone.location.isnot(None))
        .filter(ST_DWithin(zone_geography, depot_geography, radius_m))
        .all()
    )
