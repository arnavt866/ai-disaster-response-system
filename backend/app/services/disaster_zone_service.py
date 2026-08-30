from datetime import datetime

from shapely.geometry import shape
from sqlalchemy.orm import Session

from app.models.disaster_zone import DisasterZone
from app.services.geospatial.zone_geometry import point_from_lat_lon


def polygon_centroid_lat_lon(geometry: dict) -> tuple[float, float]:
    """Return latitude and longitude for a GeoJSON polygon centroid."""
    centroid = shape(geometry).centroid
    return centroid.y, centroid.x


def create_disaster_zones(
    db: Session,
    disaster_type: str,
    analyzed_cells: list[dict],
) -> int:
    """Persist analyzed grid cells as disaster zones using polygon centroids."""
    zones = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    for index, cell in enumerate(analyzed_cells, start=1):
        latitude, longitude = polygon_centroid_lat_lon(cell["geometry"])

        zone = DisasterZone(
            zone_name=f"{disaster_type.upper()}-{timestamp}-Zone-{index}",
            disaster_type=disaster_type,
            severity=cell["severity_level"],
            operational_priority=cell["severity_level"],
            latitude=latitude,
            longitude=longitude,
            location=point_from_lat_lon(latitude, longitude),
            affected_population=cell["estimated_population"],
            status="Active",
        )

        zones.append(zone)

    db.bulk_save_objects(zones)
    db.commit()

    return len(zones)