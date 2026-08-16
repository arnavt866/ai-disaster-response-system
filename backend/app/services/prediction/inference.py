"""Load trained model artifacts and run inference."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.config.settings import MODEL_DIR
from app.services.historical.feature_schema import ML_FEATURE_COLUMNS, ML_TARGET_COLUMNS
from app.services.prediction.uncertainty import ConformalIntervalEstimator
from app.services.prediction.vulnerability import (
    VulnerabilityProfile,
    compute_vulnerability_factor,
)


class ModelArtifactsNotFoundError(FileNotFoundError):
    """Raised when trained model artifacts are missing."""


@lru_cache(maxsize=1)
def load_model_registry(model_dir: str | None = None) -> dict[str, Any]:
    path = Path(model_dir) if model_dir else MODEL_DIR
    registry_file = path / "model_registry.json"
    if not registry_file.exists():
        raise ModelArtifactsNotFoundError(
            "Model registry not found. Run training first."
        )
    with registry_file.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_target_artifacts(
    target: str,
    model_dir: Path | None = None,
) -> tuple[Any, ConformalIntervalEstimator, dict[str, Any]]:
    base = model_dir or MODEL_DIR
    target_dir = base / target
    pipeline_path = target_dir / "pipeline.joblib"
    conformal_path = target_dir / "conformal.joblib"
    metadata_path = target_dir / "metadata.json"

    if not pipeline_path.exists():
        raise ModelArtifactsNotFoundError(f"Missing pipeline for target: {target}")

    pipeline = joblib.load(pipeline_path)
    conformal: ConformalIntervalEstimator = joblib.load(conformal_path)
    with metadata_path.open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    return pipeline, conformal, metadata


def build_feature_row(
    features: dict[str, Any],
    disaster_type: str | None = None,
) -> pd.DataFrame:
    """Build a single-row feature DataFrame for inference."""
    row: dict[str, Any] = {}
    for col in ML_FEATURE_COLUMNS:
        if col in {
            "disaster_type_normalized",
            "state_normalized",
            "district_normalized",
        }:
            row[col] = "Unknown"
        else:
            row[col] = 0
    row.update(features)
    if disaster_type:
        row["disaster_type_normalized"] = disaster_type
    for cat_col in (
        "disaster_type_normalized",
        "state_normalized",
        "district_normalized",
    ):
        if not row.get(cat_col):
            row[cat_col] = "Unknown"
    return pd.DataFrame([row])


def map_grid_analysis_to_features(
    grid_result: dict[str, Any],
    disaster_type: str,
    district_overlaps: list[dict[str, Any]] | None = None,
    event_year: int | None = None,
    event_month: int | None = None,
) -> dict[str, Any]:
    """
    Map Milestone-1 grid analysis output to ML feature schema.

    Historical-only impact fields default to 0 for current-event prediction.
    District/state are taken from the highest-overlap district when available.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    year = event_year or now.year
    month = event_month or now.month

    state = None
    district = None
    if district_overlaps:
        primary = max(district_overlaps, key=lambda item: item["overlap_proportion"])
        state = primary.get("state_name")
        district = primary.get("district")

    population = int(grid_result.get("estimated_population", 0))
    buildings = int(grid_result.get("building_count", 0))

    return {
        "disaster_type_normalized": disaster_type.title(),
        "event_year": year,
        "event_month": month,
        "state_normalized": state,
        "district_normalized": district,
        "deaths": 0,
        "injuries": 0,
        "missing_persons": 0,
        "affected_population": population,
        "evacuated_population": 0,
        "houses_destroyed": 0,
        "houses_damaged": 0,
        "affected_families": 0,
        "relocated_population": 0,
        "hospitals_affected": 0,
        "schools_affected": 0,
        "agricultural_hectares": 0.0,
        "livestock_heads": 0,
        "road_damage_km": 0.0,
        "duration_days": 0,
        "sector_relief": 0,
        "sector_health": 0,
        "sector_education": 0,
        "sector_agriculture": 0,
        "sector_industry": 0,
        "sector_water": 0,
        "sector_sewer": 0,
        "sector_energy": 0,
        "sector_communications": 0,
        "sector_transport": 0,
        "_severity_score": grid_result.get("severity_score"),
        "_building_count": buildings,
    }


def predict_demand(
    features: dict[str, Any],
    severity_multiplier: float = 1.0,
    vulnerability_profile: VulnerabilityProfile | None = None,
    model_dir: Path | None = None,
) -> dict[str, Any]:
    """Run inference for all four proxy demand targets."""
    registry = load_model_registry(str(model_dir) if model_dir else None)
    feature_row = build_feature_row(features)
    vuln = compute_vulnerability_factor(vulnerability_profile)
    combined_multiplier = severity_multiplier * vuln["vulnerability_factor"]

    predictions: dict[str, Any] = {}
    for target in ML_TARGET_COLUMNS:
        pipeline, conformal, metadata = load_target_artifacts(target, model_dir)
        point = float(pipeline.predict(feature_row)[0])
        point = max(0.0, point * combined_multiplier)
        lower, upper = conformal.predict_interval(np.array([point]))
        predictions[target] = {
            "point_estimate": int(round(point)),
            "prediction_interval_lower": int(round(float(lower[0]))),
            "prediction_interval_upper": int(round(float(upper[0]))),
            "selected_model": metadata["selected_model"],
            "uncertainty_method": conformal.method,
            "coverage_level": conformal.coverage_level,
        }

    return {
        "predictions": predictions,
        "target_is_observed": False,
        "target_method": "impact_based_proxy_v1",
        "model_version": registry.get("model_version"),
        "vulnerability": vuln,
        "severity_multiplier": severity_multiplier,
    }
