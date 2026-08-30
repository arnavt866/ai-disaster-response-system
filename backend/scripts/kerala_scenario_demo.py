"""SYNTHETIC illustrative demo — Kerala Floods 2018 scenario simulation.

Loads data/synthetic/kerala_floods_2018_scenario.json (NOT training data) and runs each
record through:
  1. Approved proxy target formulas (proxy_target_config.json)
  2. Existing trained Ridge model via POST /prediction/scenario

Never writes to historical_ml_dataset.csv or retrains models.

Usage:
    cd backend
    $env:PYTHONPATH="."
    python scripts/kerala_scenario_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.config.settings import MODEL_DIR, PROJECT_ROOT
from app.main import app
from app.services.historical.feature_schema import ML_FEATURE_COLUMNS
from app.services.historical.proxy_target_generator import (
    compute_proxy_targets_for_row,
    load_proxy_target_config,
)

SCENARIO_PATH = PROJECT_ROOT / "data" / "synthetic" / "kerala_floods_2018_scenario.json"

DEFAULT_SCENARIO_PARAMS = {
    "severity_multiplier": 1.2,
    "response_speed_factor": 0.8,
    "resource_availability_factor": 0.7,
}

_NUMERIC_DEFAULTS = {
    "deaths": 0,
    "injuries": 0,
    "missing_persons": 0,
    "affected_population": 0,
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
}


def load_synthetic_kerala_records(path: Path | None = None) -> list[dict]:
    """Load SYNTHETIC illustrative records only — never used for training."""
    path = path or SCENARIO_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not records:
        raise ValueError(f"No records found in {path}")
    for record in records:
        if record.get("data_source") != "synthetic_illustrative":
            raise ValueError(
                f"Refusing non-synthetic record {record.get('record_id')!r}: "
                f"data_source={record.get('data_source')!r}"
            )
    return records


def record_to_scenario_features(record: dict) -> dict:
    """Map a synthetic impact record to DemandFeatureInput-compatible features."""
    event_year, event_month, _ = record["event_date"].split("-")
    features = dict(_NUMERIC_DEFAULTS)
    for column in ML_FEATURE_COLUMNS:
        if column in record:
            features[column] = record[column]
    features["disaster_type_normalized"] = record.get("disaster_type_normalized", "Flood")
    features["event_year"] = int(event_year)
    features["event_month"] = int(event_month)
    features["state_normalized"] = record.get("state", "Kerala")
    features["district_normalized"] = record.get("district")
    return features


def run_kerala_scenario_demo(
    *,
    scenario_params: dict | None = None,
    client: TestClient | None = None,
    path: Path | None = None,
) -> list[dict]:
    """
    SYNTHETIC demo entry point: proxy formulas + existing /prediction/scenario API.

    Returns per-district result summaries. Does not touch training data or artifacts.
    """
    if not (MODEL_DIR / "model_registry.json").exists():
        raise FileNotFoundError(
            f"Trained model artifacts not found under {MODEL_DIR}. "
            "Train models before running the Kerala scenario demo."
        )

    records = load_synthetic_kerala_records(path)
    config = load_proxy_target_config()
    params = {**DEFAULT_SCENARIO_PARAMS, **(scenario_params or {})}
    http = client or TestClient(app)
    results: list[dict] = []

    for record in records:
        proxy_targets = compute_proxy_targets_for_row(record, config)
        features = record_to_scenario_features(record)
        response = http.post(
            "/prediction/scenario",
            json={"features": features, **params},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Scenario API failed for {record.get('district')}: "
                f"{response.status_code} {response.text}"
            )
        scenario_body = response.json()
        food = scenario_body["predictions"]["food_packets_demand"]
        results.append(
            {
                "record_id": record.get("record_id"),
                "district": record.get("district"),
                "event_date": record.get("event_date"),
                "data_source": record.get("data_source"),
                "proxy_targets": {
                    key: proxy_targets[key]
                    for key in (
                        "food_packets_demand",
                        "water_demand",
                        "medical_kits_demand",
                        "shelter_capacity_demand",
                    )
                },
                "model_point_estimate": food["point_estimate"],
                "scenario_adjusted_estimate": food["scenario_adjusted_estimate"],
                "target_is_observed": proxy_targets["target_is_observed"],
            }
        )
    return results


def main() -> int:
    print("=" * 60)
    print("SYNTHETIC Kerala Floods 2018 — scenario simulation demo")
    print(f"Source: {SCENARIO_PATH}")
    print("(Illustrative data only — NOT used for model training)")
    print("=" * 60)

    try:
        results = run_kerala_scenario_demo()
    except FileNotFoundError as exc:
        print(f"SKIP: {exc}", file=sys.stderr)
        return 1

    for row in results:
        print(
            f"\n{row['district']} ({row['event_date']}) [{row['data_source']}]"
        )
        print(f"  Proxy food demand:     {row['proxy_targets']['food_packets_demand']}")
        print(f"  Model point estimate:  {row['model_point_estimate']}")
        print(f"  Scenario-adjusted:     {row['scenario_adjusted_estimate']}")

    print(f"\nCompleted {len(results)} synthetic district scenario(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
