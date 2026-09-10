"""Regional drive-network graphs built from the local India OSM PBF (cached on disk)."""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import osmium
from scipy.spatial import cKDTree

from app.config.settings import OSM_FILE, PROJECT_ROOT
from app.services.optimization.routing_service import haversine_km

logger = logging.getLogger(__name__)

ROAD_GRAPHS_DIR = PROJECT_ROOT / "data" / "road_graphs"

DRIVABLE_HIGHWAY_TYPES = frozenset(
    {
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "residential",
        "unclassified",
    }
)

# Demo depot clusters: Chennai, Bhubaneswar, Delhi (relief_centers table).
DEMO_REGIONS: dict[str, dict[str, Any]] = {
    "chennai": {
        "center_lat": 13.0827,
        "center_lon": 80.2707,
        "radius_km": 75.0,
    },
    "bhubaneswar": {
        "center_lat": 20.2961,
        "center_lon": 85.8245,
        "radius_km": 50.0,
    },
    "delhi": {
        "center_lat": 28.6139,
        "center_lon": 77.2090,
        "radius_km": 50.0,
    },
}

_GRAPH_CACHE: dict[str, nx.DiGraph] = {}


@dataclass(frozen=True)
class RoadPathResult:
    distance_km: float
    coordinates: list[list[float]]  # GeoJSON [lon, lat] pairs along the road path
    region_id: str
    edges: list[dict[str, Any]]  # [{u, v, length_m}, ...]


def _graph_path(region_id: str) -> Path:
    return ROAD_GRAPHS_DIR / f"{region_id}.graphml"


def _metadata_path(region_id: str) -> Path:
    return ROAD_GRAPHS_DIR / f"{region_id}.meta.json"


def region_bbox(center_lat: float, center_lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) for a circular coverage area."""
    delta_lat = radius_km / 111.0
    cos_lat = math.cos(math.radians(center_lat)) or 1e-9
    delta_lon = radius_km / (111.0 * cos_lat)
    return (
        center_lon - delta_lon,
        center_lat - delta_lat,
        center_lon + delta_lon,
        center_lat + delta_lat,
    )


def resolve_region_for_pair(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> str | None:
    """Return a demo region id when both endpoints lie within its coverage radius."""
    for region_id, meta in DEMO_REGIONS.items():
        center_lat = meta["center_lat"]
        center_lon = meta["center_lon"]
        radius_km = meta["radius_km"]
        in_region = True
        for lat, lon in ((lat1, lon1), (lat2, lon2)):
            if haversine_km(center_lat, center_lon, lat, lon) > radius_km:
                in_region = False
                break
        if in_region:
            return region_id
    return None


def _way_intersects_bbox(
    coords: list[tuple[int, float, float]],
    bbox: tuple[float, float, float, float],
) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    for _, lat, lon in coords:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return True
    return False


def _add_way_to_graph(
    graph: nx.DiGraph,
    coords: list[tuple[int, float, float]],
    oneway_tag: str,
) -> None:
    forward = oneway_tag != "-1"
    backward = oneway_tag not in ("yes", "true", "1")

    for node_id, lat, lon in coords:
        graph.add_node(node_id, x=lon, y=lat)

    for index in range(len(coords) - 1):
        n1, lat1, lon1 = coords[index]
        n2, lat2, lon2 = coords[index + 1]
        length_m = haversine_km(lat1, lon1, lat2, lon2) * 1000.0
        if forward:
            graph.add_edge(n1, n2, length=length_m)
        if backward:
            graph.add_edge(n2, n1, length=length_m)


class _RegionalRoadGraphHandler(osmium.SimpleHandler):
    """Stream-filter drivable highway ways from the local PBF within regional bboxes."""

    def __init__(self, region_bboxes: dict[str, tuple[float, float, float, float]]) -> None:
        super().__init__()
        self.region_bboxes = region_bboxes
        self.graphs: dict[str, nx.DiGraph] = {
            region_id: nx.DiGraph() for region_id in region_bboxes
        }

    def way(self, way) -> None:
        highway = way.tags.get("highway")
        if highway not in DRIVABLE_HIGHWAY_TYPES:
            return

        coords: list[tuple[int, float, float]] = []
        for node in way.nodes:
            if not node.location.valid():
                return
            coords.append((node.ref, node.lat, node.lon))

        if len(coords) < 2:
            return

        matching_regions = [
            region_id
            for region_id, bbox in self.region_bboxes.items()
            if _way_intersects_bbox(coords, bbox)
        ]
        if not matching_regions:
            return

        oneway_tag = way.tags.get("oneway", "no")
        for region_id in matching_regions:
            _add_way_to_graph(self.graphs[region_id], coords, oneway_tag)


def _build_graphs_from_local_pbf(
    region_ids: list[str] | None = None,
) -> dict[str, nx.DiGraph]:
    """Extract regional drive graphs from the cached India PBF via one osmium pass."""
    if not OSM_FILE.exists():
        raise FileNotFoundError(f"Local OSM PBF not found: {OSM_FILE}")

    selected = region_ids or list(DEMO_REGIONS.keys())
    region_bboxes = {
        region_id: region_bbox(
            DEMO_REGIONS[region_id]["center_lat"],
            DEMO_REGIONS[region_id]["center_lon"],
            DEMO_REGIONS[region_id]["radius_km"],
        )
        for region_id in selected
    }

    logger.info(
        "Streaming local PBF for regions: %s",
        ", ".join(selected),
    )

    handler = _RegionalRoadGraphHandler(region_bboxes)
    handler.apply_file(str(OSM_FILE), locations=True)
    return handler.graphs


def _normalize_loaded_graph(graph: nx.DiGraph) -> nx.DiGraph:
    """Ensure node coordinates and edge weights are numeric after GraphML load."""
    directed = nx.DiGraph()
    for node_id, attrs in graph.nodes(data=True):
        directed.add_node(
            int(node_id) if str(node_id).isdigit() else node_id,
            x=float(attrs["x"]),
            y=float(attrs["y"]),
        )
    for u, v, attrs in graph.edges(data=True):
        u_id = int(u) if str(u).isdigit() else u
        v_id = int(v) if str(v).isdigit() else v
        directed.add_edge(u_id, v_id, length=float(attrs["length"]))
    return directed


def build_region_graph(region_id: str, *, force: bool = False) -> nx.DiGraph:
    """Build a regional drive graph from the local PBF and cache to disk."""
    if region_id not in DEMO_REGIONS:
        raise ValueError(f"Unknown road-graph region: {region_id}")

    ROAD_GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    graph_file = _graph_path(region_id)

    if graph_file.exists() and not force:
        graph = load_region_graph(region_id)
        if graph is not None:
            return graph

    graphs = _build_graphs_from_local_pbf([region_id])
    graph = graphs[region_id]
    _cache_region_graphs({region_id: graph})
    return graph


def _cache_region_graphs(graphs: dict[str, nx.DiGraph]) -> None:
    """Write built graphs and metadata to the road_graphs cache directory."""
    for region_id, graph in graphs.items():
        graph_file = _graph_path(region_id)
        meta_file = _metadata_path(region_id)
        nx.write_graphml(graph, graph_file)
        meta_file.write_text(
            json.dumps(
                {
                    "region_id": region_id,
                    "center_lat": DEMO_REGIONS[region_id]["center_lat"],
                    "center_lon": DEMO_REGIONS[region_id]["center_lon"],
                    "radius_km": DEMO_REGIONS[region_id]["radius_km"],
                    "node_count": graph.number_of_nodes(),
                    "edge_count": graph.number_of_edges(),
                    "source": str(OSM_FILE),
                    "build_method": "osmium_local_pbf",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        _GRAPH_CACHE[region_id] = graph
        logger.info(
            "Cached %s graph: %d nodes, %d edges -> %s",
            region_id,
            graph.number_of_nodes(),
            graph.number_of_edges(),
            graph_file,
        )


def load_region_graph(region_id: str) -> nx.DiGraph | None:
    """Load a cached regional graph from disk (does not rebuild on miss)."""
    if region_id in _GRAPH_CACHE:
        return _GRAPH_CACHE[region_id]

    graph_file = _graph_path(region_id)
    if not graph_file.exists():
        return None

    try:
        graph = _normalize_loaded_graph(nx.read_graphml(graph_file))
        _GRAPH_CACHE[region_id] = graph
        return graph
    except Exception as exc:
        logger.warning("Unable to load road graph for %s: %s", region_id, exc)
        return None


def _ensure_node_index(graph: nx.DiGraph) -> tuple[cKDTree, list[Any]]:
    """Build (once per graph object) a KD-tree over node lon/lat."""
    cached = graph.graph.get("_node_kdtree")
    if cached is not None:
        return cached

    nodes = list(graph.nodes)
    if not nodes:
        raise ValueError("Road graph has no nodes")

    coords = np.ascontiguousarray(
        [
            [float(graph.nodes[node]["x"]), float(graph.nodes[node]["y"])]
            for node in nodes
        ],
        dtype=np.float64,
    )
    index = (cKDTree(coords), nodes)
    graph.graph["_node_kdtree"] = index
    return index


def _nearest_node(graph: nx.DiGraph, lon: float, lat: float) -> Any:
    """Snap a coordinate to the closest graph node (O(log n) via KD-tree)."""
    tree, nodes = _ensure_node_index(graph)
    _distance, index = tree.query([lon, lat], k=1)
    return nodes[int(index)]


def _shortest_path_with_blocks(
    graph: nx.DiGraph,
    orig: Any,
    dest: Any,
    blocked: set[tuple[Any, Any]],
) -> tuple[list[Any], float]:
    if orig == dest:
        return [orig], 0.0

    routing_graph = graph
    if blocked:
        routing_graph = graph.copy()
        for u, v in blocked:
            if routing_graph.has_edge(u, v):
                routing_graph.remove_edge(u, v)

    route_nodes = nx.shortest_path(routing_graph, orig, dest, weight="length")
    distance_m = sum(
        float(routing_graph[route_nodes[i]][route_nodes[i + 1]]["length"])
        for i in range(len(route_nodes) - 1)
    )
    return route_nodes, distance_m


def compute_road_path(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> RoadPathResult | None:
    """
    Compute a road-following path when both points fall in the same cached demo region.

    Returns None when out of coverage or routing fails (caller should fall back).
    """
    region_id = resolve_region_for_pair(lat1, lon1, lat2, lon2)
    if region_id is None:
        return None

    graph = load_region_graph(region_id)
    if graph is None:
        return None

    try:
        from app.services.optimization.road_block_store import blocked_edge_set

        blocked = blocked_edge_set(region_id)
        orig = _nearest_node(graph, lon1, lat1)
        dest = _nearest_node(graph, lon2, lat2)
        if orig == dest:
            distance_m = 0.0
            route_nodes = [orig]
            path_edges: list[dict[str, Any]] = []
        else:
            route_nodes, distance_m = _shortest_path_with_blocks(
                graph, orig, dest, blocked
            )
            path_edges = [
                {
                    "u": route_nodes[i],
                    "v": route_nodes[i + 1],
                    "region_id": region_id,
                    "length_m": round(
                        float(graph[route_nodes[i]][route_nodes[i + 1]]["length"]),
                        1,
                    ),
                }
                for i in range(len(route_nodes) - 1)
            ]

        coordinates = [
            [float(graph.nodes[node]["x"]), float(graph.nodes[node]["y"])]
            for node in route_nodes
        ]
        if len(coordinates) < 2:
            coordinates = [[lon1, lat1], [lon2, lat2]]

        return RoadPathResult(
            distance_km=round(distance_m / 1000.0, 2),
            coordinates=coordinates,
            region_id=region_id,
            edges=path_edges,
        )
    except Exception as exc:
        logger.warning(
            "Road path computation failed for region %s: %s",
            region_id,
            exc,
        )
        return None


def rebuild_region_graphs(
    region_ids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build and cache one or more regional graphs from the local PBF."""
    selected = region_ids or list(DEMO_REGIONS.keys())
    started = time.perf_counter()
    graphs = _build_graphs_from_local_pbf(selected)
    elapsed = time.perf_counter() - started
    _cache_region_graphs(graphs)
    summary: dict[str, dict[str, Any]] = {}
    for region_id in selected:
        meta_path = _metadata_path(region_id)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["build_seconds"] = round(elapsed, 2)
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            summary[region_id] = meta
    return summary


def ensure_demo_graphs_built(
    *,
    force: bool = False,
    region_ids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Pre-build demo regional graphs from the local PBF; returns per-region metadata."""
    selected = region_ids or list(DEMO_REGIONS.keys())
    missing_or_stale = force or any(
        not _graph_path(region_id).exists() for region_id in selected
    )
    if missing_or_stale:
        return rebuild_region_graphs(selected)

    summary: dict[str, dict[str, Any]] = {}
    for region_id in selected:
        meta_path = _metadata_path(region_id)
        if meta_path.exists():
            summary[region_id] = json.loads(meta_path.read_text(encoding="utf-8"))
    return summary


def clear_graph_cache() -> None:
    """Clear in-memory graph cache (disk cache is preserved)."""
    _GRAPH_CACHE.clear()
