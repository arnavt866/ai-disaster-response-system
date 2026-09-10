"""Road-network routing tests (local OSM graph + NetworkX with Haversine fallback)."""

import networkx as nx
import pytest

from app.services.optimization import road_graph
from app.services.optimization.routing_service import build_road_route, build_route, nearest_depot


def _tiny_bhubaneswar_graph() -> nx.DiGraph:
    """Minimal drive graph for unit tests (no PBF read required)."""
    graph = nx.DiGraph()
    graph.add_node(1, y=20.2961, x=85.8245)
    graph.add_node(2, y=20.3100, x=85.8400)
    graph.add_node(3, y=20.3500, x=85.8800)
    graph.add_edge(1, 2, length=4500.0)
    graph.add_edge(2, 3, length=8000.0)
    return graph


@pytest.fixture
def patched_bhubaneswar_graph(monkeypatch):
    graph = _tiny_bhubaneswar_graph()

    def _load(region_id: str):
        return graph if region_id == "bhubaneswar" else None

    monkeypatch.setattr(road_graph, "load_region_graph", _load)
    monkeypatch.setattr(
        road_graph,
        "resolve_region_for_pair",
        lambda *_args, **_kwargs: "bhubaneswar",
    )


def test_road_route_returns_valid_path(patched_bhubaneswar_graph):
    route = build_road_route(
        depot_id=6,
        depot_name="Bhubaneswar Depot",
        depot_lat=20.2961,
        depot_lon=85.8245,
        zone_id=100,
        zone_name="EQ Zone",
        zone_lat=20.3500,
        zone_lon=85.8800,
    )
    assert route["routing_method"] == "road_network_local_osm"
    assert route["geometry"]["type"] == "LineString"
    assert len(route["geometry"]["coordinates"]) >= 3
    assert route["distance_km"] == 12.5
    assert route["estimated_travel_hours"] > 0


def test_nearest_node_matches_linear_scan():
    graph = _tiny_bhubaneswar_graph()
    lon, lat = 85.8500, 20.3200
    kd_node = road_graph._nearest_node(graph, lon, lat)
    linear_node = min(
        graph.nodes,
        key=lambda node: (
            (float(graph.nodes[node]["x"]) - lon) ** 2
            + (float(graph.nodes[node]["y"]) - lat) ** 2
        ),
    )
    assert kd_node == linear_node
    assert road_graph._nearest_node(graph, lon, lat) == kd_node


def test_road_route_falls_back_to_haversine():
    route = build_road_route(
        depot_id=1,
        depot_name="Remote Depot",
        depot_lat=51.5074,
        depot_lon=-0.1278,
        zone_id=2,
        zone_name="Remote Zone",
        zone_lat=51.5200,
        zone_lon=-0.1000,
    )
    assert route["routing_method"] == "haversine_distance_prototype"
    assert route["geometry"]["type"] == "LineString"
    assert len(route["geometry"]["coordinates"]) == 2
    assert route["distance_km"] > 0

    baseline = build_route(
        depot_id=1,
        depot_name="Remote Depot",
        depot_lat=51.5074,
        depot_lon=-0.1278,
        zone_id=2,
        zone_name="Remote Zone",
        zone_lat=51.5200,
        zone_lon=-0.1000,
    )
    assert route["distance_km"] == baseline["distance_km"]
    assert route["estimated_travel_hours"] == baseline["estimated_travel_hours"]


def test_nearest_depot_uses_road_route(patched_bhubaneswar_graph):
    depots = [
        {
            "id": 6,
            "name": "Bhubaneswar Depot",
            "latitude": 20.2961,
            "longitude": 85.8245,
            "zone_id": 100,
            "zone_name": "EQ Zone",
        },
        {
            "id": 99,
            "name": "Far Depot",
            "latitude": 20.3500,
            "longitude": 85.8800,
            "zone_id": 100,
            "zone_name": "EQ Zone",
        },
    ]
    route = nearest_depot(20.3100, 85.8400, depots)
    assert route is not None
    assert route["depot_id"] == 6
    assert route["routing_method"] == "road_network_local_osm"
