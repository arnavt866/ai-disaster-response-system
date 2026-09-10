"""Isolated depot + inventory seeding for M3 integration tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def seed_isolated_depot(
    client: TestClient,
    *,
    zone_name: str = "M3 Isolated Zone",
    affected_population: int = 800,
    quantities: dict[str, int] | None = None,
) -> tuple[int, int, str]:
    """Create a unique relief center + inventory for this test.

    Rows are written through TestClient / ``get_db``. The autouse SAVEPOINT
    fixture in ``conftest.py`` rolls them back so they never persist in the
    shared database (or they land only in ``TEST_DATABASE_URL`` if that is set).
    Unique depot names still avoid colliding with committed production rows
    that are visible inside the same transaction.
    """
    quantities = quantities or {
        "food": 5000,
        "water": 10000,
        "medical": 500,
        "shelter": 2000,
    }

    zone_resp = client.post(
        "/zones/",
        json={
            "zone_name": zone_name,
            "disaster_type": "Flood",
            "severity": "High",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "affected_population": affected_population,
            "status": "Active",
            "operational_priority": "High",
        },
    )
    assert zone_resp.status_code == 200
    zone_id = zone_resp.json()["id"]

    depot_name = f"M3 Depot {uuid.uuid4().hex[:8]}"
    depot_resp = client.post(
        "/relief-centers/",
        json={
            "name": depot_name,
            "address": "Isolated test depot",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "capacity": 10000,
            "available_capacity": 10000,
            "status": "Active",
        },
    )
    assert depot_resp.status_code == 200
    depot_id = depot_resp.json()["id"]

    for category, qty in quantities.items():
        inv_resp = client.post(
            "/inventory/",
            json={
                "resource_name": f"{category} stock",
                "category": category,
                "quantity": qty,
                "unit": "units",
                "warehouse": depot_name,
                "status": "Available",
            },
        )
        assert inv_resp.status_code == 200

    return zone_id, depot_id, depot_name
