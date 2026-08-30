"""Regression tests for DisasterZone centroid persistence."""

from unittest.mock import MagicMock

from shapely.geometry import mapping, box

from app.models.disaster_zone import DisasterZone
from app.services.disaster_zone_service import (
    create_disaster_zones,
    polygon_centroid_lat_lon,
)
from app.services.prediction.zone_integration_service import build_grid_geojson_from_zone


def test_polygon_centroid_lat_lon_uses_geometric_centroid_not_first_vertex():
    polygon = box(85.0, 20.0, 85.02, 20.02)
    geojson = mapping(polygon)

    first_vertex = geojson["coordinates"][0][0]
    latitude, longitude = polygon_centroid_lat_lon(geojson)

    assert (longitude, latitude) != tuple(first_vertex)
    assert abs(latitude - 20.01) < 1e-9
    assert abs(longitude - 85.01) < 1e-9


def test_create_disaster_zones_persists_polygon_centroid():
    polygon = box(85.0, 20.0, 85.02, 20.02)
    analyzed_cells = [
        {
            "geometry": mapping(polygon),
            "severity_level": "Moderate",
            "estimated_population": 100,
        }
    ]

    mock_db = MagicMock()
    saved_zones: list[DisasterZone] = []

    def capture_bulk_save(zones):
        saved_zones.extend(zones)

    mock_db.bulk_save_objects.side_effect = capture_bulk_save

    count = create_disaster_zones(mock_db, "FL", analyzed_cells)

    assert count == 1
    expected_lat, expected_lon = polygon_centroid_lat_lon(analyzed_cells[0]["geometry"])
    assert saved_zones[0].latitude == expected_lat
    assert saved_zones[0].longitude == expected_lon
    assert saved_zones[0].location is not None
    assert "POINT" in saved_zones[0].location.desc


def test_zone_integration_rebuilds_grid_from_persisted_centroid():
    zone = DisasterZone(
        id=1,
        zone_name="TEST-ZONE",
        disaster_type="FL",
        severity="Moderate",
        latitude=20.01,
        longitude=85.01,
        affected_population=100,
        status="Active",
    )

    geojson = build_grid_geojson_from_zone(zone)

    assert geojson["type"] in {"Polygon", "MultiPolygon"}
    rebuilt_lat, rebuilt_lon = polygon_centroid_lat_lon(geojson)
    assert abs(rebuilt_lat - zone.latitude) < 1e-9
    assert abs(rebuilt_lon - zone.longitude) < 1e-9
