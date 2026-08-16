"""Tests for prediction API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.config.settings import MODEL_DIR
from app.main import app

client = TestClient(app)


def test_prediction_model_endpoint_or_503():
    response = client.get("/prediction/model")
    assert response.status_code in {200, 503}


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_prediction_demand_valid_request():
    payload = {
        "features": {
            "disaster_type_normalized": "Flood",
            "event_year": 2018,
            "event_month": 8,
            "state_normalized": "Odisha",
            "district_normalized": "Cuttack",
            "affected_population": 500,
            "injuries": 2,
        },
        "severity_multiplier": 1.0,
    }
    response = client.post("/prediction/demand", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["target_is_observed"] is False
    assert "food_packets_demand" in body["resource_estimates"]
    assert "prediction_interval_lower" in body["resource_estimates"]["food_packets_demand"]


def test_prediction_demand_invalid_request():
    response = client.post("/prediction/demand", json={"features": {}})
    assert response.status_code == 422


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_prediction_scenario_endpoint():
    payload = {
        "features": {
            "disaster_type_normalized": "Cyclone",
            "event_year": 2019,
            "event_month": 10,
            "state_normalized": "Odisha",
            "district_normalized": "Puri",
            "affected_population": 1200,
        },
        "severity_multiplier": 1.5,
        "response_speed_factor": 1.0,
        "resource_availability_factor": 0.8,
    }
    response = client.post("/prediction/scenario", json=payload)
    assert response.status_code == 200
    assert "scenario_parameters" in response.json()


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_prediction_history_endpoint():
    response = client.get("/prediction/history")
    assert response.status_code == 200
    assert "entries" in response.json()


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_prediction_grid_demand_smoke():
    payload = {
        "grid_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [85.8, 20.2],
                    [85.81, 20.2],
                    [85.81, 20.21],
                    [85.8, 20.21],
                    [85.8, 20.2],
                ]
            ],
        },
        "disaster_type": "FL",
        "estimated_population": 500,
        "building_count": 10,
        "severity_score": 60,
        "severity_level": "Moderate",
    }
    response = client.post("/prediction/demand/grid", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "resource_estimates" in body
    assert "district_overlap" in body


def test_prediction_model_503_when_artifacts_missing(monkeypatch):
    from app.services.prediction.inference import ModelArtifactsNotFoundError

    def _raise(*_args, **_kwargs):
        raise ModelArtifactsNotFoundError("missing")

    monkeypatch.setattr(
        "app.api.prediction_routes.load_model_registry",
        _raise,
    )
    response = client.get("/prediction/model")
    assert response.status_code == 503


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_prediction_evaluation_endpoint():
    response = client.get("/prediction/evaluation")
    assert response.status_code == 200
    assert "comparison_table" in response.json()

