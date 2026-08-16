"""Dynamic demand recalculation for current disaster/grid conditions."""

from __future__ import annotations

from typing import Any

from app.services.prediction.inference import (
    map_grid_analysis_to_features,
    predict_demand,
)
from app.services.prediction.vulnerability import VulnerabilityProfile


def recalculate_grid_demand(
    grid_result: dict[str, Any],
    disaster_type: str,
    district_overlaps: list[dict[str, Any]] | None = None,
    severity_multiplier: float = 1.0,
    vulnerability_profile: VulnerabilityProfile | None = None,
    field_report_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Recalculate demand for a current grid cell using trained model artifacts.

    Does not retrain the model. Optional field_report_overrides can supply
    updated impact estimates (e.g. injuries, evacuated population).
    """
    features = map_grid_analysis_to_features(
        grid_result=grid_result,
        disaster_type=disaster_type,
        district_overlaps=district_overlaps,
    )
    if field_report_overrides:
        for key, value in field_report_overrides.items():
            if key in features:
                features[key] = value

    prediction = predict_demand(
        features=features,
        severity_multiplier=severity_multiplier,
        vulnerability_profile=vulnerability_profile,
    )

    return {
        "grid_features": {
            k: v for k, v in features.items() if not k.startswith("_")
        },
        "district_overlaps": district_overlaps or [],
        "prediction": prediction,
        "rule_based_resources": {
            "food_packets": grid_result.get("food_packets"),
            "water_bottles": grid_result.get("water_bottles"),
            "medical_kits": grid_result.get("medical_kits"),
            "temporary_shelters": grid_result.get("temporary_shelters"),
        },
    }
