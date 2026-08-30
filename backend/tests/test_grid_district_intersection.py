"""Tests for grid/district polygon intersection."""

import json

import pytest
from shapely.geometry import shape

from app.config.settings import TARGET_DISTRICTS_GEOJSON
from app.services.geospatial.grid_district_service import (
    PROJECTED_CRS,
    compute_grid_district_overlaps,
    enrich_grid_with_districts,
    load_target_districts_gdf,
)
from app.services.historical.district_validator import validate_target_districts_geojson


def test_target_districts_load_and_validate():
    validation = validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    assert validation.valid
    assert validation.feature_count == 80
    gdf = load_target_districts_gdf()
    assert len(gdf) == 80


def test_grid_district_overlap_proportions_sum_to_one():
    with TARGET_DISTRICTS_GEOJSON.open(encoding="utf-8") as handle:
        geo = json.load(handle)

    # Use first district geometry as a test grid polygon.
    feature = geo["features"][0]
    overlaps = compute_grid_district_overlaps(feature["geometry"])
    assert len(overlaps) >= 1
    total = sum(item["overlap_proportion"] for item in overlaps)
    assert abs(total - 1.0) < 1e-5
    assert overlaps[0]["state_name"] in {"Odisha", "Tamil Nadu", "Uttarakhand"}


def test_enrich_grid_reports_multi_district_flag():
    with TARGET_DISTRICTS_GEOJSON.open(encoding="utf-8") as handle:
        geo = json.load(handle)

    # Build a bbox spanning multiple districts in Tamil Nadu if possible.
    coords = []
    for feat in geo["features"][:5]:
        geom = shape(feat["geometry"])
        minx, miny, maxx, maxy = geom.bounds
        coords.extend([(minx, miny), (maxx, maxy)])

    minx = min(c[0] for c in coords)
    miny = min(c[1] for c in coords)
    maxx = max(c[0] for c in coords)
    maxy = max(c[1] for c in coords)

    grid_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny],
        ]],
    }
    result = enrich_grid_with_districts(grid_geojson)
    assert result["crs_used_for_area"] == PROJECTED_CRS
    assert "overlaps" in result
    if result["district_count"] > 1:
        assert result["multi_district"] is True
        total = sum(item["overlap_proportion"] for item in result["overlaps"])
        assert abs(total - 1.0) < 1e-5


def test_cross_boundary_grid_multiple_districts_from_intersection_not_centroid():
    """Grid spanning adjacent districts must retain all intersecting districts."""
    with TARGET_DISTRICTS_GEOJSON.open(encoding="utf-8") as handle:
        geo = json.load(handle)

    features = geo["features"][:8]
    bounds = [shape(feat["geometry"]).bounds for feat in features]
    minx = min(b[0] for b in bounds)
    miny = min(b[1] for b in bounds)
    maxx = max(b[2] for b in bounds)
    maxy = max(b[3] for b in bounds)

    grid_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny],
        ]],
    }
    overlaps = compute_grid_district_overlaps(grid_geojson)
    assert len(overlaps) >= 2
    total = sum(item["overlap_proportion"] for item in overlaps)
    assert abs(total - 1.0) < 1e-5
    districts = {item["district"] for item in overlaps}
    assert len(districts) >= 2
