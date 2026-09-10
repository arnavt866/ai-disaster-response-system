"""Tests for demo road-graph edge blocking."""

import networkx as nx
import pytest

from app.services.optimization import road_graph
from app.services.optimization.road_block_store import (
    add_blocked_edge,
    clear_blocked_edges,
    list_blocked_edges,
    remove_blocked_edge,
)
from app.services.optimization.routing_service import build_road_route


def _tiny_bhubaneswar_graph() -> nx.DiGraph:
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
    clear_blocked_edges("bhubaneswar")
    yield
    clear_blocked_edges("bhubaneswar")


def test_blocked_edge_store_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.optimization.road_block_store.BLOCKS_FILE",
        tmp_path / "blocked_edges.json",
    )
    add_blocked_edge("chennai", 10, 20)
    blocks = list_blocked_edges("chennai")
    assert len(blocks) == 1
    assert blocks[0]["u"] == 10
    remove_blocked_edge("chennai", 10, 20)
    assert list_blocked_edges("chennai") == []


def test_blocked_segment_falls_back_to_haversine(patched_bhubaneswar_graph):
    add_blocked_edge("bhubaneswar", 1, 2)
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
    assert route["routing_method"] == "haversine_distance_prototype"
    assert route["distance_km"] > 0


def test_unblocked_road_route_includes_path_edges(patched_bhubaneswar_graph):
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
    assert len(route["path_edges"]) == 2
    assert route["path_edges"][0]["u"] == 1
