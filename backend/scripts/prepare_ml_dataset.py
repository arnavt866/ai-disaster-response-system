#!/usr/bin/env python
"""CLI entry point for Phase B2 proxy-target generation and ML dataset build."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.historical.phase_b2_preparation import run_phase_b2  # noqa: E402


def main() -> int:
    result = run_phase_b2()
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
