"""Integrate Milestone-1 DisasterZone records with Milestone-2 prediction."""

from __future__ import annotations

from typing import Any

from shapely.geometry import box, mapping
from sqlalchemy.orm import Session

from app.config.settings import DEFAULT_RADIUS, GRID_CELL_SIZE
from app.models.disaster_zone import DisasterZone
from app.services.geospatial.grid_analysis_service import analyze_grid
from app.services.geospatial.grid_district_service import enrich_grid_with_districts
from app.services.geospatial.population_service import WORLDPOP_AGE_SEX_SOURCE
from app.services.prediction.demand_service import recalculate_grid_demand
from app.services.prediction.inference import load_model_registry
from app.services.prediction.prediction_history import record_prediction
from app.services.prediction.vulnerability import VulnerabilityProfile
from app.services.zone_service import get_zone_by_id

# Approximate severity scores aligned with Milestone-1 severity levels.
SEVERITY_LEVEL_SCORES: dict[str, int] = {
    "Critical": 85,
    "High": 70,
    "Moderate": 50,
    "Low": 30,
}


def build_grid_geojson_from_zone(zone: DisasterZone) -> dict[str, Any]:
    """
    Reconstruct a Milestone-1-sized grid cell polygon from a zone centroid.

    Milestone-1 stores zone centroids (not full geometry) when persisting zones,
    so the grid cell is rebuilt using the same GRID_CELL_SIZE convention.
    """
    half = GRID_CELL_SIZE / 2
    cell = box(
        zone.longitude - half,
        zone.latitude - half,
        zone.longitude + half,
        zone.latitude + half,
    )
    return mapping(cell)


def profile_from_zone_cache(zone: DisasterZone) -> VulnerabilityProfile | None:
    """Read precomputed WorldPop age/sex shares. Does not open rasters."""
    if not getattr(zone, "vulnerability_data_available", False):
        return None
    return VulnerabilityProfile(
        elderly_ratio=zone.elderly_ratio,
        children_ratio=zone.children_ratio,
        data_available=True,
        source=zone.vulnerability_source or WORLDPOP_AGE_SEX_SOURCE,
    )


def predict_demand_for_zone(
    db: Session,
    zone_id: int,
    *,
    severity_multiplier: float = 1.0,
    vulnerability_profile: VulnerabilityProfile | None = None,
    field_report_overrides: dict[str, Any] | None = None,
    update_source: str = "disaster_zone",
    satellite_placeholder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Predict demand for an existing Milestone-1 DisasterZone.

    Flow:
    DisasterZone (M1) → grid cell geometry → M1 analyze_grid features
    → district overlaps → M2 model prediction.
    """
    zone = get_zone_by_id(db, zone_id)
    if zone is None:
        raise ValueError(f"Disaster zone {zone_id} not found")

    if vulnerability_profile is None:
        vulnerability_profile = profile_from_zone_cache(zone)

    grid_geojson = build_grid_geojson_from_zone(zone)

    # Reuse Milestone-1 grid analysis (population, buildings, severity, rule resources).
    grid_result = analyze_grid(
        db=db,
        grid_geojson=grid_geojson,
        radius_km=DEFAULT_RADIUS,
    )

    # Preserve zone-level severity/population from the persisted M1 record.
    grid_result["severity_level"] = zone.severity
    grid_result["severity_score"] = SEVERITY_LEVEL_SCORES.get(zone.severity, 50)
    grid_result["estimated_population"] = zone.affected_population

    district_overlap = enrich_grid_with_districts(grid_geojson)

    if satellite_placeholder:
        # Placeholder only — no fabricated satellite damage assessment.
        field_report_overrides = {
            **(field_report_overrides or {}),
            "_satellite_status": satellite_placeholder.get("status", "placeholder"),
        }

    demand_result = recalculate_grid_demand(
        grid_result=grid_result,
        disaster_type=zone.disaster_type,
        district_overlaps=district_overlap["overlaps"],
        severity_multiplier=severity_multiplier,
        vulnerability_profile=vulnerability_profile,
        field_report_overrides=field_report_overrides,
    )

    registry = load_model_registry()
    history_entry = record_prediction(
        zone_id=zone.id,
        grid_reference=zone.zone_name,
        update_source=update_source,
        model_version=registry.get("model_version"),
        predictions=demand_result["prediction"]["predictions"],
        metadata={
            "disaster_type": zone.disaster_type,
            "severity": zone.severity,
            "affected_population": zone.affected_population,
            "field_report_overrides": field_report_overrides or {},
            "satellite_placeholder": satellite_placeholder,
        },
    )

    return {
        "zone_id": zone.id,
        "zone_name": zone.zone_name,
        "disaster_type": zone.disaster_type,
        "severity": zone.severity,
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "source": "disaster_zone",
        "grid_geojson": grid_geojson,
        "milestone1_grid_analysis": grid_result,
        "district_overlap": district_overlap,
        "demand": demand_result,
        "prediction_history_id": history_entry["history_id"],
    }
