"""Scenario simulation smoke tests."""

import pytest
from fastapi.testclient import TestClient

from app.config.settings import MODEL_DIR
from app.main import app
from app.services.prediction.scenario_service import simulate_demand_scenario

client = TestClient(app)

BASE_FEATURES = {
    "disaster_type_normalized": "Flood",
    "event_year": 2019,
    "event_month": 8,
    "state_normalized": "Odisha",
    "district_normalized": "Cuttack",
    "affected_population": 2000,
    "injuries": 20,
    "evacuated_population": 500,
}


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_slower_response_increases_effective_severity_demand():
    fast = simulate_demand_scenario(
        features=BASE_FEATURES,
        severity_multiplier=1.0,
        response_speed_factor=2.0,
        resource_availability_factor=1.0,
    )
    slow = simulate_demand_scenario(
        features=BASE_FEATURES,
        severity_multiplier=1.0,
        response_speed_factor=0.5,
        resource_availability_factor=1.0,
    )
    fast_food = fast["predictions"]["food_packets_demand"]["point_estimate"]
    slow_food = slow["predictions"]["food_packets_demand"]["point_estimate"]
    assert slow_food > fast_food


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_lower_resource_availability_increases_scenario_adjusted_estimate():
    abundant = simulate_demand_scenario(
        features=BASE_FEATURES,
        resource_availability_factor=1.0,
    )
    scarce = simulate_demand_scenario(
        features=BASE_FEATURES,
        resource_availability_factor=0.5,
    )
    abundant_adj = abundant["predictions"]["food_packets_demand"]["scenario_adjusted_estimate"]
    scarce_adj = scarce["predictions"]["food_packets_demand"]["scenario_adjusted_estimate"]
    assert scarce_adj > abundant_adj


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_scenario_api_smoke():
    payload = {
        "features": BASE_FEATURES,
        "severity_multiplier": 1.2,
        "response_speed_factor": 0.8,
        "resource_availability_factor": 0.7,
    }
    response = client.post("/prediction/scenario", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "scenario_parameters" in body
    assert body["scenario_parameters"]["response_speed_factor"] == 0.8
