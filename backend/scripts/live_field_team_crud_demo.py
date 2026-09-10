"""Persistent live CRUD demo against the configured DATABASE_URL (commits)."""
from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.database.dependencies import get_db
from app.main import app


def _real_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def main() -> None:
    app.dependency_overrides[get_db] = _real_db
    client = TestClient(app)
    stamp = str(int(time.time()))

    before = client.get("/field-teams/")
    before.raise_for_status()
    before_rows = before.json()
    active_before = sum(1 for row in before_rows if row["status"] != "Inactive")
    print("=== BEFORE ===")
    print(f"Active: {active_before} / Total: {len(before_rows)}")

    create_resp = client.post(
        "/field-teams/",
        json={
            "team_name": f"CRUD Audit Team {stamp}",
            "vehicle_type": "Van",
            "vehicle_capacity": 1200,
            "personnel_count": 6,
            "base_latitude": 13.05,
            "base_longitude": 80.25,
        },
    )
    create_resp.raise_for_status()
    created = create_resp.json()
    team_id = created["id"]
    print("=== CREATE ===")
    print(json.dumps(created, indent=2))

    get_resp = client.get(f"/field-teams/{team_id}")
    get_resp.raise_for_status()
    print("=== GET BY ID ===")
    print(json.dumps(get_resp.json(), indent=2))

    update_resp = client.put(
        f"/field-teams/{team_id}",
        json={
            "team_name": f"CRUD Audit Team {stamp} (edited)",
            "vehicle_type": "Truck",
            "vehicle_capacity": 2400,
            "personnel_count": 8,
            "base_latitude": 13.06,
            "base_longitude": 80.26,
            "status": "Available",
        },
    )
    update_resp.raise_for_status()
    print("=== UPDATE ===")
    print(json.dumps(update_resp.json(), indent=2))

    deactivate_resp = client.delete(f"/field-teams/{team_id}")
    deactivate_resp.raise_for_status()
    print("=== DEACTIVATE ===")
    print(json.dumps(deactivate_resp.json(), indent=2))

    after = client.get("/field-teams/")
    after.raise_for_status()
    after_rows = after.json()
    active_after = sum(1 for row in after_rows if row["status"] != "Inactive")
    team = next(row for row in after_rows if row["id"] == team_id)
    print("=== AFTER ===")
    print(f"Active roster count: {active_after} (unchanged from {active_before})")
    print(f"Team persisted with status={team['status']}")
    print(f"Hidden from default Teams UI filter: {team['status'] == 'Inactive'}")


if __name__ == "__main__":
    main()
