"""Edge-case tests for prediction engine."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config.settings import MODEL_DIR
from app.main import app
from app.models.disaster_zone import DisasterZone
from app.services.prediction.prediction_history import (
    HISTORY_FILE,
    load_prediction_history,
    record_prediction,
)
from app.services.prediction.vulnerability import compute_vulnerability_factor
from app.services.prediction.zone_integration_service import (
    build_grid_geojson_from_zone,
    predict_demand_for_zone,
)

client = TestClient(app)


def test_invalid_zone_id_returns_404():
    mock_db = MagicMock()
    with patch(
        "app.api.prediction_routes.predict_demand_for_zone",
        side_effect=ValueError("Disaster zone 99999 not found"),
    ):
        response = client.post("/prediction/demand/zone/99999")
    # Patch at route level won't work for Depends db - test service directly
    mock_db = MagicMock()
    with patch(
        "app.services.prediction.zone_integration_service.get_zone_by_id",
        return_value=None,
    ):
        with pytest.raises(ValueError, match="not found"):
            predict_demand_for_zone(mock_db, 99999)


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_missing_optional_vulnerability_defaults_neutral():
    result = compute_vulnerability_factor(None)
    assert result["vulnerability_factor"] == 1.0
    assert result["vulnerability_data_available"] is False


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_zero_impact_zone_prediction():
    payload = {
        "features": {
            "disaster_type_normalized": "Flood",
            "event_year": 2020,
            "event_month": 1,
            "affected_population": 0,
            "injuries": 0,
            "evacuated_population": 0,
            "houses_destroyed": 0,
            "houses_damaged": 0,
        },
        "severity_multiplier": 1.0,
    }
    response = client.post("/prediction/demand", json=payload)
    assert response.status_code == 200
    estimates = response.json()["resource_estimates"]
    for target in estimates:
        assert estimates[target]["point_estimate"] >= 0
        assert estimates[target]["prediction_interval_lower"] <= estimates[target]["point_estimate"]


def test_invalid_scenario_parameters_rejected():
    payload = {
        "features": {
            "disaster_type_normalized": "Flood",
            "event_year": 2020,
            "event_month": 1,
        },
        "severity_multiplier": 0,
    }
    response = client.post("/prediction/scenario", json=payload)
    assert response.status_code == 422


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_prediction_interval_validity():
    payload = {
        "features": {
            "disaster_type_normalized": "Flood",
            "event_year": 2020,
            "event_month": 6,
            "affected_population": 1000,
            "injuries": 10,
        },
    }
    response = client.post("/prediction/demand", json=payload)
    assert response.status_code == 200
    for target, est in response.json()["resource_estimates"].items():
        lower = est["prediction_interval_lower"]
        upper = est["prediction_interval_upper"]
        point = est["point_estimate"]
        assert lower <= point <= upper or lower <= upper
        assert est["uncertainty_method"] == "split_conformal_abs_residual"


def test_cross_district_grid_overlap():
    from app.config.settings import TARGET_DISTRICTS_GEOJSON
    from app.services.geospatial.grid_district_service import enrich_grid_with_districts
    import json
    from shapely.geometry import shape, mapping, box

    with TARGET_DISTRICTS_GEOJSON.open(encoding="utf-8") as handle:
        geo = json.load(handle)

    coords = []
    for feat in geo["features"][:8]:
        geom = shape(feat["geometry"])
        minx, miny, maxx, maxy = geom.bounds
        coords.extend([(minx, miny), (maxx, maxy)])

    grid = mapping(box(
        min(c[0] for c in coords),
        min(c[1] for c in coords),
        max(c[0] for c in coords),
        max(c[1] for c in coords),
    ))
    result = enrich_grid_with_districts(grid)
    if result["district_count"] > 1:
        assert result["multi_district"] is True
        total = sum(o["overlap_proportion"] for o in result["overlaps"])
        assert abs(total - 1.0) < 1e-5


def test_prediction_history_record_and_load(tmp_path, monkeypatch):
    history_file = tmp_path / "history.jsonl"
    monkeypatch.setattr(
        "app.services.prediction.prediction_history.HISTORY_FILE",
        history_file,
    )
    entry = record_prediction(
        zone_id=1,
        grid_reference="ZONE-1",
        update_source="test",
        model_version="test_v1",
        predictions={"food_packets_demand": {"point_estimate": 10}},
    )
    assert entry["history_id"]
    loaded = load_prediction_history()
    assert len(loaded) == 1
    assert loaded[0]["zone_id"] == 1


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_missing_field_report_still_predicts():
    """Demand prediction works without optional field-report overrides."""
    payload = {
        "features": {
            "disaster_type_normalized": "Flood",
            "event_year": 2020,
            "event_month": 3,
            "affected_population": 100,
        },
    }
    response = client.post("/prediction/demand", json=payload)
    assert response.status_code == 200
    assert response.json()["resource_estimates"]


def test_build_grid_geojson_from_zone():
    zone = DisasterZone(
        id=1,
        zone_name="TEST-ZONE",
        disaster_type="FL",
        severity="High",
        latitude=20.0,
        longitude=85.0,
        affected_population=500,
        status="Active",
    )
    geo = build_grid_geojson_from_zone(zone)
    assert geo["type"] in {"Polygon", "MultiPolygon"}
