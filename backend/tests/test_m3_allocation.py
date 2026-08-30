"""Milestone 3 allocation, routing, missions, and priority tests."""

import pytest
from fastapi.testclient import TestClient

from app.config.settings import MODEL_DIR
from app.main import app
from app.services.optimization.routing_service import build_route, haversine_km
from tests.m3_isolated_seed import seed_isolated_depot

client = TestClient(app)


def test_haversine_distance_positive():
    distance = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert distance > 1000


def test_route_geometry_open_status():
    route = build_route(
        depot_id=1,
        depot_name="Depot A",
        depot_lat=20.0,
        depot_lon=85.0,
        zone_id=2,
        zone_name="Zone B",
        zone_lat=20.5,
        zone_lon=85.5,
        blocked=False,
    )
    assert route["feasible"] is True
    assert route["route_status"] == "open"
    assert route["geometry"]["type"] == "LineString"


def test_allocation_status_endpoint():
    response = client.get("/allocation/status")
    assert response.status_code == 200
    assert "ortools" in response.json()["algorithm"]


def test_priority_override_invalid_zone():
    response = client.post(
        "/allocation/zones/999999/priority",
        json={"priority": "High"},
    )
    assert response.status_code == 404


def test_analytics_dashboard_endpoint():
    response = client.get("/analytics/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "active_zones" in body
    assert body["data_source"] == "database"


def test_field_team_crud_flow():
    # NOTE: Writes field_teams rows directly to whatever DB the test client uses; no teardown (known test-isolation gap).
    create_resp = client.post(
        "/field-teams/",
        json={
            "team_name": "Alpha Response",
            "vehicle_type": "Truck",
            "vehicle_capacity": 5000,
        },
    )
    assert create_resp.status_code == 200
    team_id = create_resp.json()["id"]

    list_resp = client.get("/field-teams/")
    assert list_resp.status_code == 200
    assert any(team["id"] == team_id for team in list_resp.json())

    status_resp = client.patch(
        f"/field-teams/{team_id}/status",
        json={"status": "Assigned"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "Assigned"


def test_assign_team_to_mission():
    # NOTE: Writes field_teams rows directly to whatever DB the test client uses; no teardown (known test-isolation gap).
    zone_resp = client.post(
        "/zones/",
        json={
            "zone_name": "Assign Team Zone",
            "disaster_type": "Flood",
            "severity": "High",
            "latitude": 20.2961,
            "longitude": 85.8245,
            "affected_population": 500,
            "status": "Active",
            "operational_priority": "High",
        },
    )
    assert zone_resp.status_code == 200
    zone_id = zone_resp.json()["id"]

    team_resp = client.post(
        "/field-teams/",
        json={"team_name": "Assignable Crew", "vehicle_type": "Van", "vehicle_capacity": 1000},
    )
    assert team_resp.status_code == 200
    team_id = team_resp.json()["id"]
    assert team_resp.json()["status"] == "Available"

    mission_resp = client.post(
        "/missions/",
        json={"zone_id": zone_id, "priority": "High"},
    )
    assert mission_resp.status_code == 200
    mission_id = mission_resp.json()["id"]
    assert mission_resp.json()["field_team_id"] is None

    assign_resp = client.patch(
        f"/missions/{mission_id}/team",
        json={"field_team_id": team_id},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["field_team_id"] == team_id

    team_after = client.get("/field-teams/")
    assigned_team = next(row for row in team_after.json() if row["id"] == team_id)
    assert assigned_team["status"] == "Assigned"


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_allocation_optimize_with_seed_data():
    # NOTE: Writes field_teams rows directly to whatever DB the test client uses; no teardown (known test-isolation gap).
    zone_id, depot_id, depot_name = seed_isolated_depot(
        client,
        zone_name="M3 Test Zone",
        affected_population=1200,
    )

    alloc_resp = client.post(
        "/allocation/optimize",
        json={"zone_ids": [zone_id], "persist": True},
    )
    assert alloc_resp.status_code == 200
    alloc_body = alloc_resp.json()
    assert alloc_body["status"] == "ok"
    assert alloc_body["zone_count"] == 1
    assert alloc_body["target_is_observed"] is False
    assert len(alloc_body["allocations"]) >= 4

    priority_resp = client.post(
        f"/allocation/zones/{zone_id}/priority",
        json={"priority": "Critical"},
    )
    assert priority_resp.status_code == 200

    recalc_resp = client.post(f"/allocation/zones/{zone_id}/recalculate")
    assert recalc_resp.status_code == 200

    route_resp = client.post(
        "/allocation/route",
        json={"relief_center_id": depot_id, "zone_id": zone_id},
    )
    assert route_resp.status_code == 200
    assert route_resp.json()["distance_km"] >= 0

    flow_depot_id = next(
        (flow["relief_center_id"] for flow in alloc_body.get("flows", []) if flow["zone_id"] == zone_id),
        depot_id,
    )

    team_resp = client.post(
        "/field-teams/",
        json={"team_name": "Mission Team", "vehicle_type": "Truck", "vehicle_capacity": 3000},
    )
    team_id = team_resp.json()["id"]

    mission_resp = client.post(
        "/missions/",
        json={
            "zone_id": zone_id,
            "field_team_id": team_id,
            "relief_center_id": flow_depot_id,
            "priority": "Critical",
            "resources_payload": {
                "run_id": alloc_body["run_id"],
                "zone_id": zone_id,
                "items": [row for row in alloc_body["allocations"] if row["zone_id"] == zone_id],
                "flows": [row for row in alloc_body.get("flows", []) if row["zone_id"] == zone_id],
            },
        },
    )
    assert mission_resp.status_code == 200
    mission_id = mission_resp.json()["id"]

    for status in ["Dispatched", "In Transit", "Delivered"]:
        patch_resp = client.patch(
            f"/missions/{mission_id}/status",
            json={"status": status},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == status

    history_resp = client.get("/allocation/history")
    assert history_resp.status_code == 200
    assert history_resp.json()["total"] >= 4
