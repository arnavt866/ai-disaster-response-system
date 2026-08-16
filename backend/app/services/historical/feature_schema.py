"""Machine-learning feature schema for historical training data."""

from __future__ import annotations

# Columns used as model input features (historical training).
ML_FEATURE_COLUMNS: tuple[str, ...] = (
    "disaster_type_normalized",
    "event_year",
    "event_month",
    "state_normalized",
    "district_normalized",
    "deaths",
    "injuries",
    "missing_persons",
    "affected_population",
    "evacuated_population",
    "houses_destroyed",
    "houses_damaged",
    "affected_families",
    "relocated_population",
    "hospitals_affected",
    "schools_affected",
    "agricultural_hectares",
    "livestock_heads",
    "road_damage_km",
    "duration_days",
    "sector_relief",
    "sector_health",
    "sector_education",
    "sector_agriculture",
    "sector_industry",
    "sector_water",
    "sector_sewer",
    "sector_energy",
    "sector_communications",
    "sector_transport",
)

# Proxy target columns (not observed ground truth).
ML_TARGET_COLUMNS: tuple[str, ...] = (
    "food_packets_demand",
    "water_demand",
    "medical_kits_demand",
    "shelter_capacity_demand",
)

# Provenance / identifier columns preserved in the ML dataset.
ML_PROVENANCE_COLUMNS: tuple[str, ...] = (
    "record_id",
    "source_state",
    "target_method",
    "target_is_observed",
    "target_version",
    "relief_population_proxy",
)

ML_DATASET_COLUMNS: tuple[str, ...] = (
    *ML_PROVENANCE_COLUMNS,
    *ML_FEATURE_COLUMNS,
    *ML_TARGET_COLUMNS,
)
