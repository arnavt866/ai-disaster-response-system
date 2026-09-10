"""In-memory + JSON persistence for demo road-graph edge blocks."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.services.optimization.road_graph import ROAD_GRAPHS_DIR

BLOCKS_FILE = ROAD_GRAPHS_DIR / "blocked_edges.json"
_LOCK = threading.Lock()


def _load_raw() -> list[dict[str, Any]]:
    if not BLOCKS_FILE.exists():
        return []
    try:
        data = json.loads(BLOCKS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_raw(blocks: list[dict[str, Any]]) -> None:
    ROAD_GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    BLOCKS_FILE.write_text(json.dumps(blocks, indent=2), encoding="utf-8")


def _edge_key(region_id: str, u: Any, v: Any) -> tuple[str, str, str]:
    return (region_id, str(u), str(v))


def list_blocked_edges(region_id: str | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        blocks = _load_raw()
    if region_id is None:
        return blocks
    return [row for row in blocks if row.get("region_id") == region_id]


def blocked_edge_set(region_id: str) -> set[tuple[Any, Any]]:
    return {
        (row["u"], row["v"])
        for row in list_blocked_edges(region_id)
    }


def add_blocked_edge(region_id: str, u: Any, v: Any) -> dict[str, Any]:
    entry = {"region_id": region_id, "u": u, "v": v}
    with _LOCK:
        blocks = _load_raw()
        key = _edge_key(region_id, u, v)
        existing = {
            _edge_key(row["region_id"], row["u"], row["v"]) for row in blocks
        }
        if key not in existing:
            blocks.append(entry)
            _save_raw(blocks)
    return entry


def remove_blocked_edge(region_id: str, u: Any, v: Any) -> bool:
    key = _edge_key(region_id, u, v)
    with _LOCK:
        blocks = _load_raw()
        kept = [
            row
            for row in blocks
            if _edge_key(row["region_id"], row["u"], row["v"]) != key
        ]
        removed = len(kept) != len(blocks)
        if removed:
            _save_raw(kept)
    return removed


def clear_blocked_edges(region_id: str | None = None) -> int:
    with _LOCK:
        blocks = _load_raw()
        if region_id is None:
            removed = len(blocks)
            _save_raw([])
            return removed
        kept = [row for row in blocks if row.get("region_id") != region_id]
        removed = len(blocks) - len(kept)
        _save_raw(kept)
    return removed
