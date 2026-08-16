#!/usr/bin/env python
"""CLI entry point for Phase B1 historical data preparation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as `python scripts/prepare_historical_data.py` from backend/.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.historical.data_preparation import run_phase_b1  # noqa: E402


def main() -> int:
    try:
        result = run_phase_b1()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
