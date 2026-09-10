import math

from app.config.settings import (
    KM_PER_DEGREE,
    DEFAULT_RADIUS,
    DEFAULT_EARTHQUAKE_RADIUS,
    DEFAULT_FLOOD_RADIUS,
    DEFAULT_CYCLONE_RADIUS,
)

# Canonical codes used by estimate_impact_radius (GDACS-style).
_IMPACT_TYPE_ALIASES: dict[str, str] = {
    "EQ": "EQ",
    "EARTHQUAKE": "EQ",
    "FL": "FL",
    "FLOOD": "FL",
    "TC": "TC",
    "CYCLONE": "TC",
    "TROPICAL CYCLONE": "TC",
    "HURRICANE": "TC",
    "TYPHOON": "TC",
}


def normalize_impact_disaster_type(disaster_type: str) -> str:
    """Map feed-specific labels (e.g. USGS ``Earthquake``) to GDACS-style codes."""
    key = disaster_type.strip().upper()
    return _IMPACT_TYPE_ALIASES.get(key, key)


def estimate_impact_radius(
    disaster_type: str,
    magnitude: float | None = None,
    alert_level: str | None = None,
) -> float:
    """
    Estimate impact radius (km) from disaster type and optional magnitude/alert.
    Heuristic only; satellite damage assessment is not integrated.
    """

    disaster_type = normalize_impact_disaster_type(disaster_type)

    if disaster_type == "EQ":
        if magnitude is None:
            return 20

        if magnitude >= 8:
            return 250

        if magnitude >= 7:
            return 150

        if magnitude >= 6:
            return 80

        if magnitude >= 5:
            return 40

        return DEFAULT_EARTHQUAKE_RADIUS

    if disaster_type == "FL":

        if alert_level == "Red":
            return 120

        if alert_level == "Orange":
            return 80

        return DEFAULT_FLOOD_RADIUS

    if disaster_type == "TC":

        if alert_level == "Red":
            return 200

        if alert_level == "Orange":
            return 150

        return DEFAULT_CYCLONE_RADIUS

    return DEFAULT_RADIUS


def generate_circle_polygon(
    latitude: float,
    longitude: float,
    radius_km: float,
    points: int = 48,
):
    """
    Generates an approximate GeoJSON polygon.
    """

    coordinates = []

    for i in range(points):

        angle = 2 * math.pi * i / points

        dx = radius_km * math.cos(angle)
        dy = radius_km * math.sin(angle)

        lat = latitude + dy / KM_PER_DEGREE

        lon = longitude + dx / (
            KM_PER_DEGREE * math.cos(math.radians(latitude))
        )

        coordinates.append([lon, lat])

    coordinates.append(coordinates[0])

    return {
        "type": "Polygon",
        "coordinates": [coordinates]
    }


def compute_impact_area(
    latitude: float,
    longitude: float,
    disaster_type: str,
    magnitude: float | None = None,
    alert_level: str | None = None,
):

    radius = estimate_impact_radius(
        disaster_type,
        magnitude,
        alert_level,
    )

    polygon = generate_circle_polygon(
        latitude,
        longitude,
        radius,
    )

    return {

        "radius_km": radius,

        "impact_area_sq_km": round(
            math.pi * radius * radius,
            2,
        ),

        "polygon": polygon,
    }