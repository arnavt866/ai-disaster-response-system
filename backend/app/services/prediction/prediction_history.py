"""Append-only prediction history for dynamic recalibration auditing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import DATASET_DIR

HISTORY_FILE = DATASET_DIR / "prediction_history.jsonl"


def record_prediction(
    *,
    zone_id: int | None,
    grid_reference: str | None,
    update_source: str,
    model_version: str | None,
    predictions: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one prediction event without retraining the model."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "history_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zone_id": zone_id,
        "grid_reference": grid_reference,
        "update_source": update_source,
        "model_version": model_version,
        "predictions": predictions,
        "metadata": metadata or {},
    }

    with HISTORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str) + "\n")

    return entry


def load_prediction_history(limit: int = 100) -> list[dict[str, Any]]:
    """Load recent prediction history entries."""
    if not HISTORY_FILE.exists():
        return []

    entries: list[dict[str, Any]] = []
    with HISTORY_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    return entries[-limit:]
