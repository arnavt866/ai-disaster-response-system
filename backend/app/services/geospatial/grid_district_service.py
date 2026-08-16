"""Grid-to-district polygon intersection with overlap proportions."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import geopandas as gpd
from shapely.geometry import shape

from app.config.settings import TARGET_DISTRICTS_GEOJSON
from app.services.historical.district_validator import validate_target_districts_geojson

# EPSG:7755 — projected CRS used for area-based polygon intersection.
PROJECTED_CRS = "EPSG:7755"
GEOGRAPHIC_CRS = "EPSG:4326"


@lru_cache(maxsize=1)
def load_target_districts_gdf() -> gpd.GeoDataFrame:
    """Load and validate the 80-district target-state GeoJSON."""
    validation = validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    if not validation.valid:
        raise ValueError(
            "Target districts GeoJSON validation failed: "
            + "; ".join(validation.errors)
        )

    gdf = gpd.read_file(TARGET_DISTRICTS_GEOJSON)
    if gdf.crs is None:
        gdf = gdf.set_crs(GEOGRAPHIC_CRS)
    return gdf


def compute_grid_district_overlaps(
    grid_geojson: dict,
    districts_gdf: gpd.GeoDataFrame | None = None,
) -> list[dict[str, Any]]:
    """
    Compute one-to-many grid/district overlaps using polygon intersection.

    Overlap proportions are calculated in a projected CRS and
    normalized to sum to 1.0 across all intersecting districts.
    """
    districts = districts_gdf if districts_gdf is not None else load_target_districts_gdf()

    grid_gdf = gpd.GeoDataFrame(
        geometry=[shape(grid_geojson)],
        crs=GEOGRAPHIC_CRS,
    )

    grid_proj = grid_gdf.to_crs(PROJECTED_CRS)
    districts_proj = districts.to_crs(PROJECTED_CRS)

    grid_geom = grid_proj.geometry.iloc[0]
    grid_area = grid_geom.area
    if grid_area <= 0:
        return []

    overlaps: list[dict[str, Any]] = []
    for _, row in districts_proj.iterrows():
        intersection = grid_geom.intersection(row.geometry)
        if intersection.is_empty:
            continue

        overlap_area = float(intersection.area)
        if overlap_area <= 0:
            continue

        overlaps.append(
            {
                "state_name": row.get("state_name") or row.get("state"),
                "district": row.get("district"),
                "overlap_area_sq_m": round(overlap_area, 2),
                "overlap_proportion": overlap_area / grid_area,
            }
        )

    total = sum(item["overlap_proportion"] for item in overlaps)
    if total > 0:
        for item in overlaps:
            item["overlap_proportion"] = round(item["overlap_proportion"] / total, 6)

    return overlaps


def enrich_grid_with_districts(
    grid_geojson: dict,
) -> dict[str, Any]:
    """Return grid district overlap summary."""
    overlaps = compute_grid_district_overlaps(grid_geojson)
    return {
        "district_count": len(overlaps),
        "multi_district": len(overlaps) > 1,
        "overlaps": overlaps,
        "crs_used_for_area": PROJECTED_CRS,
    }
