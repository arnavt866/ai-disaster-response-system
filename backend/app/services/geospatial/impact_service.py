import math

from app.config.settings import (
    KM_PER_DEGREE,
    DEFAULT_RADIUS,
    DEFAULT_EARTHQUAKE_RADIUS,
    DEFAULT_FLOOD_RADIUS,
    DEFAULT_CYCLONE_RADIUS,
)


def estimate_impact_radius(
    disaster_type: str,
    magnitude: float | None = None,
    alert_level: str | None = None,
) -> float:
    """
    Estimate the approximate impact radius (km)
    for a disaster event.

    NOTE:
    This is a heuristic model for Milestone 1.
    Later satellite imagery will replace this.
    """

    disaster_type = disaster_type.upper()

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