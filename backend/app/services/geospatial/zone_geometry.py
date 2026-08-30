"""PostGIS point helpers for disaster zone coordinates."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement


def point_from_lat_lon(latitude: float, longitude: float) -> WKTElement:
    """Build a WGS84 POINT geometry from scalar latitude/longitude columns."""
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)
