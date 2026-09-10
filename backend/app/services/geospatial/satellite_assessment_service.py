"""Query Copernicus EMS Rapid Mapping polygons against zones/points."""

from __future__ import annotations

from typing import Any

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Area, ST_Intersects, ST_Intersection, ST_MakeEnvelope
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.config.settings import GRID_CELL_SIZE
from app.models.disaster_zone import DisasterZone
from app.models.satellite_assessment import SatelliteAssessment

CEMS_SOURCE_LABEL = "Copernicus EMS observed mapping, Cyclone Fani 2019"
CLASSIFICATION_RANK = {
    "Destroyed": 50,
    "Damaged": 40,
    "Possibly damaged": 30,
    "Flooded area": 20,
    "Flood trace": 10,
    "Not Analysed": 1,
}


def _point_geom(longitude: float, latitude: float):
    return func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)


def _zone_cell_geom(zone: DisasterZone):
    half = GRID_CELL_SIZE / 2
    return ST_MakeEnvelope(
        zone.longitude - half,
        zone.latitude - half,
        zone.longitude + half,
        zone.latitude + half,
        4326,
    )


def _rank(classification: str | None) -> int:
    return CLASSIFICATION_RANK.get((classification or "").strip(), 0)


def _summarize(
    rows: list[SatelliteAssessment],
    *,
    overlap_m2: float,
    cell_m2: float,
) -> dict[str, Any]:
    classifications = [row.classification for row in rows if row.classification]
    primary = max(classifications, key=_rank) if classifications else None
    return {
        "in_coverage": True,
        "inundated_fraction": (
            overlap_m2 / cell_m2 if cell_m2 > 0 else (1.0 if rows else 0.0)
        ),
        "overlapping_area_m2": overlap_m2,
        "severity": primary,
        "classification": primary,
        "classifications": sorted(set(classifications)),
        "feature_count": len(rows),
        "product_types": sorted({row.product_type for row in rows}),
        "activation_code": rows[0].activation_code if rows else None,
        "event_name": rows[0].event_name if rows else None,
        "source_label": CEMS_SOURCE_LABEL,
        "source_license": rows[0].source_license if rows else None,
        "source_url": rows[0].source_url if rows else None,
    }


def query_satellite_assessments_at_point(
    db: Session,
    latitude: float,
    longitude: float,
) -> dict[str, Any] | None:
    """ST_Intersects a WGS84 point against imported CEMS polygons."""
    point = _point_geom(longitude, latitude)
    rows = (
        db.query(SatelliteAssessment)
        .filter(ST_Intersects(SatelliteAssessment.geometry, point))
        .all()
    )
    if not rows:
        return None
    overlap_m2 = float(
        sum(float(row.area_m2 or 0) for row in rows if row.product_type == "delineation")
        or sum(float(row.area_m2 or 0) for row in rows)
    )
    return _summarize(rows, overlap_m2=overlap_m2, cell_m2=0.0)


def query_satellite_assessments_for_zone(
    db: Session,
    zone: DisasterZone,
) -> dict[str, Any] | None:
    """ST_Intersects a reconstructed grid cell against CEMS polygons.

    Same PostGIS spatial-predicate style as ``get_zones_near_depot`` (ST_DWithin).
    """
    cell = _zone_cell_geom(zone)
    overlap_expr = ST_Area(
        cast(ST_Intersection(SatelliteAssessment.geometry, cell), Geography)
    )
    results = (
        db.query(SatelliteAssessment, overlap_expr.label("overlap_m2"))
        .filter(ST_Intersects(SatelliteAssessment.geometry, cell))
        .all()
    )
    if not results:
        return None
    rows = [row for row, _overlap in results]
    overlap_m2 = float(sum(float(overlap or 0) for _row, overlap in results))
    cell_m2 = float(db.scalar(ST_Area(cast(cell, Geography))) or 0.0)
    return _summarize(rows, overlap_m2=overlap_m2, cell_m2=cell_m2)
