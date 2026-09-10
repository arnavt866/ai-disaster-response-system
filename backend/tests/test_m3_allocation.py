"""Milestone 3 allocation, routing, missions, and priority tests."""

from types import SimpleNamespace

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from app.config.settings import MODEL_DIR
from app.main import app
from app.services.optimization import road_graph
from app.services.optimization.allocation_service import (
    _cached_route_distance_km,
    _solve_allocation_lp,
    _solve_category_transportation,
    allocation_objective_coefficient,
    compute_depot_transport_capacity_kg,
)
from app.services.optimization.routing_service import (
    build_road_route,
    build_route,
    haversine_km,
    route_distance_km,
)
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


def test_lp_coefficient_uses_road_distance_when_covered(monkeypatch):
    """Covered depot-zone pairs must penalize road path length, not Haversine."""
    graph = nx.DiGraph()
    graph.add_node(1, y=20.2961, x=85.8245)
    graph.add_node(2, y=20.3100, x=85.8400)
    graph.add_node(3, y=20.3500, x=85.8800)
    graph.add_edge(1, 2, length=4500.0)
    graph.add_edge(2, 3, length=8000.0)

    monkeypatch.setattr(
        road_graph,
        "load_region_graph",
        lambda region_id: graph if region_id == "bhubaneswar" else None,
    )
    monkeypatch.setattr(
        road_graph,
        "resolve_region_for_pair",
        lambda *_args, **_kwargs: "bhubaneswar",
    )

    depot_lat, depot_lon = 20.2961, 85.8245
    zone_lat, zone_lon = 20.3500, 85.8800
    priority_weight = 3.0

    haversine_distance = haversine_km(depot_lat, depot_lon, zone_lat, zone_lon)
    road_distance = route_distance_km(depot_lat, depot_lon, zone_lat, zone_lon)
    haversine_coeff = allocation_objective_coefficient(
        priority_weight,
        haversine_distance,
    )
    road_coeff = allocation_objective_coefficient(priority_weight, road_distance)

    print(
        "LP coefficient proof pair "
        f"(depot {depot_lat},{depot_lon} -> zone {zone_lat},{zone_lon}): "
        f"haversine_km={haversine_distance:.4f} road_km={road_distance:.4f} "
        f"old_coeff={haversine_coeff:.4f} new_coeff={road_coeff:.4f}"
    )

    assert road_distance == 12.5
    assert road_distance != pytest.approx(haversine_distance, rel=1e-6, abs=1e-6)
    assert road_distance > haversine_distance
    assert road_coeff == pytest.approx(priority_weight * 1000.0 - 12.5)
    assert haversine_coeff == pytest.approx(
        priority_weight * 1000.0 - haversine_distance
    )
    assert road_coeff != pytest.approx(haversine_coeff, rel=1e-6, abs=1e-6)
    assert road_coeff < haversine_coeff

    depot = SimpleNamespace(
        id=6,
        name="Bhubaneswar Depot",
        latitude=depot_lat,
        longitude=depot_lon,
    )
    summaries, flows = _solve_category_transportation(
        category="food",
        zone_demands=[
            {
                "zone_id": 100,
                "zone_name": "EQ Zone",
                "latitude": zone_lat,
                "longitude": zone_lon,
                "priority_weight": priority_weight,
                "demand_by_category": {"food": 10.0},
            }
        ],
        depot_supply={6: {"food": 50.0}},
        depots={6: depot},
    )
    assert summaries[0]["allocated"] == pytest.approx(10.0)
    assert flows[0]["allocated"] == pytest.approx(10.0)
    flow_route = flows[0]["route"]
    assert flow_route["routing_method"] == "road_network_local_osm"
    assert flow_route["distance_km"] == pytest.approx(road_distance)

    cache: dict[tuple[int, int], dict] = {}
    first = _cached_route_distance_km(
        cache, 6, depot_lat, depot_lon, 100, zone_lat, zone_lon,
        depot_name="Bhubaneswar Depot",
        zone_name="EQ Zone",
    )
    second = _cached_route_distance_km(
        cache, 6, depot_lat, depot_lon, 100, zone_lat, zone_lon,
        depot_name="Bhubaneswar Depot",
        zone_name="EQ Zone",
    )
    assert first == second == 12.5
    assert cache[(6, 100)]["distance_km"] == 12.5
    assert cache[(6, 100)]["routing_method"] == "road_network_local_osm"


def test_lp_reuses_road_path_for_flow_geometry(monkeypatch):
    """LP objective and flow overlay must share one compute_road_path call per pair."""
    graph = nx.DiGraph()
    graph.add_node(1, y=20.2961, x=85.8245)
    graph.add_node(2, y=20.3100, x=85.8400)
    graph.add_node(3, y=20.3500, x=85.8800)
    graph.add_edge(1, 2, length=4500.0)
    graph.add_edge(2, 3, length=8000.0)

    monkeypatch.setattr(
        road_graph,
        "load_region_graph",
        lambda region_id: graph if region_id == "bhubaneswar" else None,
    )
    monkeypatch.setattr(
        road_graph,
        "resolve_region_for_pair",
        lambda *_args, **_kwargs: "bhubaneswar",
    )

    calls = {"n": 0}
    real_compute = road_graph.compute_road_path

    def _counting_compute(*args, **kwargs):
        calls["n"] += 1
        return real_compute(*args, **kwargs)

    monkeypatch.setattr(road_graph, "compute_road_path", _counting_compute)

    depot = SimpleNamespace(
        id=6,
        name="Bhubaneswar Depot",
        latitude=20.2961,
        longitude=85.8245,
    )
    _solve_category_transportation(
        category="food",
        zone_demands=[
            {
                "zone_id": 100,
                "zone_name": "EQ Zone",
                "latitude": 20.3500,
                "longitude": 85.8800,
                "priority_weight": 3.0,
                "demand_by_category": {"food": 10.0},
            }
        ],
        depot_supply={6: {"food": 50.0}},
        depots={6: depot},
    )
    assert calls["n"] == 1


def _stub_road_route(**_kwargs):
    return {
        "distance_km": 1.0,
        "routing_method": "stub",
        "geometry": {"type": "LineString", "coordinates": [[85.0, 20.0], [85.1, 20.1]]},
    }


def test_lp_caps_allocation_at_depot_transport_capacity(monkeypatch):
    """Fleet payload, not warehouse stock, must bind when trucks are the bottleneck."""
    monkeypatch.setattr(
        "app.services.optimization.allocation_service.build_road_route",
        _stub_road_route,
    )

    depot = SimpleNamespace(
        id=1,
        name="Capacity Test Depot",
        latitude=20.2961,
        longitude=85.8245,
    )
    zone_demands = [
        {
            "zone_id": 200,
            "zone_name": "Capacity Zone",
            "latitude": 20.3100,
            "longitude": 85.8400,
            "priority_weight": 3.0,
            "demand_by_category": {"food": 1000.0, "water": 1000.0},
        }
    ]
    depot_supply = {1: {"food": 5000.0, "water": 5000.0}}
    unit_weights = {"food": 1.0, "water": 1.0}
    shared_kwargs = {
        "zone_demands": zone_demands,
        "depot_supply": depot_supply,
        "depots": {1: depot},
        "categories": ("food", "water"),
        "unit_weights": unit_weights,
    }

    summaries_before, flows_before = _solve_allocation_lp(
        **shared_kwargs,
        depot_capacity_kg=None,
    )
    summaries_after, flows_after = _solve_allocation_lp(
        **shared_kwargs,
        depot_capacity_kg={1: 80.0},
    )

    before_total = sum(flow["allocated"] for flow in flows_before)
    after_total = sum(flow["allocated"] for flow in flows_after)
    after_kg = sum(
        flow["allocated"] * unit_weights[flow["resource_category"]]
        for flow in flows_after
    )
    print(
        "Transport-capacity proof (depot 1, food+water demand 1000 each, "
        "inventory 5000 each, unit_weight=1 kg): "
        f"BEFORE allocated_units={before_total:.2f} (no fleet cap) | "
        f"AFTER allocated_units={after_total:.2f} after_kg={after_kg:.2f} "
        "(fleet cap 80 kg shared across categories)"
    )

    assert before_total == pytest.approx(2000.0)
    assert after_kg == pytest.approx(80.0, abs=0.05)
    assert after_total == pytest.approx(80.0, abs=0.05)
    assert after_total < before_total


def test_unlinked_depot_uses_default_payload_constant():
    depot = SimpleNamespace(id=9, name="Isolated Depot", latitude=0.0, longitude=0.0)
    capacity = compute_depot_transport_capacity_kg({9: depot}, teams=[])
    from app.services.optimization.constants import DEFAULT_DEPOT_DAILY_PAYLOAD_KG

    assert capacity[9] == DEFAULT_DEPOT_DAILY_PAYLOAD_KG


@pytest.mark.skipif(
    not (road_graph.ROAD_GRAPHS_DIR / "chennai.graphml").exists(),
    reason="Cached Chennai OSM road graph not present",
)
def test_flow_route_distance_matches_lp_objective_chennai():
    """Map flow geometry must use the same road distance as the LP coefficient."""
    depot_lat, depot_lon = 13.0827, 80.2707
    zone_lat, zone_lon = 13.1000, 80.2900
    depot = SimpleNamespace(
        id=1,
        name="Chennai Depot",
        latitude=depot_lat,
        longitude=depot_lon,
    )

    before_route = build_route(
        depot_id=1,
        depot_name="Chennai Depot",
        depot_lat=depot_lat,
        depot_lon=depot_lon,
        zone_id=101,
        zone_name="Chennai Zone",
        zone_lat=zone_lat,
        zone_lon=zone_lon,
    )
    expected_road_route = build_road_route(
        depot_id=1,
        depot_name="Chennai Depot",
        depot_lat=depot_lat,
        depot_lon=depot_lon,
        zone_id=101,
        zone_name="Chennai Zone",
        zone_lat=zone_lat,
        zone_lon=zone_lon,
    )
    objective_distance = route_distance_km(
        depot_lat, depot_lon, zone_lat, zone_lon
    )

    summaries, flows = _solve_category_transportation(
        category="food",
        zone_demands=[
            {
                "zone_id": 101,
                "zone_name": "Chennai Zone",
                "latitude": zone_lat,
                "longitude": zone_lon,
                "priority_weight": 3.0,
                "demand_by_category": {"food": 10.0},
            }
        ],
        depot_supply={1: {"food": 50.0}},
        depots={1: depot},
    )

    flow_route = flows[0]["route"]
    print(
        "Chennai depot-zone flow route proof "
        f"(depot {depot_lat},{depot_lon} -> zone {zone_lat},{zone_lon}): "
        f"BEFORE distance_km={before_route['distance_km']} "
        f"routing_method={before_route['routing_method']} | "
        f"AFTER distance_km={flow_route['distance_km']} "
        f"routing_method={flow_route['routing_method']} | "
        f"objective route_distance_km={objective_distance}"
    )

    assert summaries[0]["allocated"] == pytest.approx(10.0)
    assert flow_route["routing_method"] == "road_network_local_osm"
    assert expected_road_route["routing_method"] == "road_network_local_osm"
    assert flow_route["distance_km"] == pytest.approx(objective_distance, abs=0.01)
    assert flow_route["distance_km"] == pytest.approx(
        expected_road_route["distance_km"], abs=1e-9
    )
    assert flow_route["distance_km"] != pytest.approx(
        before_route["distance_km"], abs=0.01
    )
    assert len(flow_route["geometry"]["coordinates"]) > 2


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
    create_resp = client.post(
        "/field-teams/",
        json={
            "team_name": "Alpha Response",
            "vehicle_type": "Truck",
            "vehicle_capacity": 5000,
            "personnel_count": 8,
            "base_latitude": 13.08,
            "base_longitude": 80.27,
        },
    )
    assert create_resp.status_code == 200
    team_id = create_resp.json()["id"]

    get_resp = client.get(f"/field-teams/{team_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["team_name"] == "Alpha Response"
    assert get_resp.json()["personnel_count"] == 8

    list_resp = client.get("/field-teams/")
    assert list_resp.status_code == 200
    assert any(team["id"] == team_id for team in list_resp.json())

    update_resp = client.put(
        f"/field-teams/{team_id}",
        json={
            "team_name": "Alpha Response Updated",
            "vehicle_type": "Heavy Truck",
            "vehicle_capacity": 6000,
            "personnel_count": 10,
            "base_latitude": 13.09,
            "base_longitude": 80.28,
            "status": "Available",
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["team_name"] == "Alpha Response Updated"
    assert update_resp.json()["vehicle_capacity"] == 6000

    status_resp = client.patch(
        f"/field-teams/{team_id}/status",
        json={"status": "Assigned"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "Assigned"

    deactivate_resp = client.delete(f"/field-teams/{team_id}")
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["status"] == "Inactive"

    missing_resp = client.get("/field-teams/999999")
    assert missing_resp.status_code == 404


def test_assign_team_to_mission():
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


def test_allocation_optimize_rejects_unbounded_without_confirm():
    resp = client.post(
        "/allocation/optimize",
        json={"zone_ids": None, "persist": False},
    )
    assert resp.status_code == 400
    assert "confirm" in resp.json()["detail"].lower()

    empty = client.post(
        "/allocation/optimize",
        json={"zone_ids": [], "persist": False},
    )
    assert empty.status_code == 400
