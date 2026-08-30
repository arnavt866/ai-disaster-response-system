"""Pre-build cached regional road graphs from the local India OSM PBF (no live Overpass)."""

from __future__ import annotations

import argparse
import json
import sys
import time

from app.services.optimization.road_graph import (
    DEMO_REGIONS,
    ROAD_GRAPHS_DIR,
    clear_graph_cache,
    ensure_demo_graphs_built,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build cached OSM road graphs for demo depot regions.",
    )
    parser.add_argument(
        "--region",
        action="append",
        choices=sorted(DEMO_REGIONS.keys()),
        help="Build only the named region(s); may be repeated. Default: all regions.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even when cache files already exist.",
    )
    args = parser.parse_args()

    regions = args.region or sorted(DEMO_REGIONS.keys())
    print(f"Building road graph(s): {', '.join(regions)}")
    print(f"Cache directory: {ROAD_GRAPHS_DIR}")
    clear_graph_cache()
    started = time.perf_counter()
    summary = ensure_demo_graphs_built(force=args.force, region_ids=regions)
    elapsed = time.perf_counter() - started
    print(json.dumps(summary, indent=2))
    print(f"Total elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
