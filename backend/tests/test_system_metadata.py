"""Tests for system metadata endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_system_metadata_exposes_workflow_enums():
    response = client.get("/system/metadata")
    assert response.status_code == 200
    body = response.json()
    assert body["operational_priorities"] == ["Critical", "High", "Moderate", "Low"]
    assert "Created" in body["mission_transitions"]
    assert set(body["mission_transitions"]["Created"]) == {"Allocated", "Dispatched"}
    assert body["available_field_team_status"] == "Available"
    assert body["inactive_field_team_status"] == "Inactive"
    assert len(body["demand_targets"]) == 4
    assert body["demand_targets"][0]["inventory_category"] in {"food", "water", "medical", "shelter"}
