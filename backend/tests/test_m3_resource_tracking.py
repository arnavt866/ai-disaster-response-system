"""Resource tracking lifecycle tests."""

import pytest
from fastapi.testclient import TestClient

from app.config.settings import MODEL_DIR
from app.main import app
from tests.m3_isolated_seed import seed_isolated_depot

client = TestClient(app)


def _seed_depot_inventory():
    return seed_isolated_depot(client, zone_name="Tracking Zone")


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_inventory_reserved_after_allocation():
    zone_id, _, depot_name = _seed_depot_inventory()
    before = client.get("/inventory/").json()
    food_before = next(item for item in before if item["category"] == "food" and item["warehouse"] == depot_name)

    alloc = client.post(
        "/allocation/optimize",
        json={"zone_ids": [zone_id], "persist": True},
    )
    assert alloc.status_code == 200
    alloc_body = alloc.json()
    assert alloc_body["status"] == "ok"
    assert alloc_body["total_allocated"] > 0

    after = client.get("/inventory/").json()
    reserved_before = sum(item.get("reserved_quantity", 0) for item in before)
    reserved_after = sum(item.get("reserved_quantity", 0) for item in after)
    assert reserved_after > reserved_before


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_recalculate_does_not_double_reserve():
    zone_id, depot_id, depot_name = _seed_depot_inventory()
    first = client.post(
        "/allocation/optimize",
        json={"zone_ids": [zone_id], "persist": True},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["status"] == "ok"

    flow_depot_names = {
        flow["relief_center_name"]
        for flow in first_body.get("flows", [])
        if flow["zone_id"] == zone_id
    }
    assert flow_depot_names, "Expected allocation flows for the isolated zone"

    def _depot_totals(items):
        depot_items = [
            item for item in items if item.get("warehouse") in flow_depot_names
        ]
        return {
            "reserved": sum(item.get("reserved_quantity", 0) for item in depot_items),
            "quantity": sum(item.get("quantity", 0) for item in depot_items),
        }

    after_first = _depot_totals(client.get("/inventory/").json())
    assert after_first["reserved"] > 0

    recalc = client.post(f"/allocation/zones/{zone_id}/recalculate")
    assert recalc.status_code == 200
    assert recalc.json()["status"] == "ok"

    after_recalc = _depot_totals(client.get("/inventory/").json())
    assert after_recalc["reserved"] == after_first["reserved"]
    assert after_recalc["quantity"] == after_first["quantity"]


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_mission_payload_dict_contract():
    zone_id, depot_id, depot_name = _seed_depot_inventory()
    alloc = client.post(
        "/allocation/optimize",
        json={"zone_ids": [zone_id], "persist": True},
    ).json()

    payload = {
        "run_id": alloc["run_id"],
        "zone_id": zone_id,
        "items": [row for row in alloc["allocations"] if row["zone_id"] == zone_id],
        "flows": [row for row in alloc["flows"] if row["zone_id"] == zone_id],
    }

    mission_resp = client.post(
        "/missions/",
        json={
            "zone_id": zone_id,
            "relief_center_id": depot_id,
            "priority": "High",
            "resources_payload": payload,
        },
    )
    assert mission_resp.status_code == 200
    assert mission_resp.json()["status"] == "Allocated"


def test_mission_payload_rejects_array():
    response = client.post(
        "/missions/",
        json={
            "zone_id": 1,
            "resources_payload": [{"food": 1}],
        },
    )
    assert response.status_code == 422


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_mission_dispatch_and_delivery_inventory():
    zone_id, depot_id, depot_name = _seed_depot_inventory()
    alloc = client.post(
        "/allocation/optimize",
        json={"zone_ids": [zone_id], "persist": True},
    ).json()
    payload = {
        "run_id": alloc["run_id"],
        "zone_id": zone_id,
        "items": [row for row in alloc["allocations"] if row["zone_id"] == zone_id],
        "flows": [row for row in alloc.get("flows", []) if row["zone_id"] == zone_id],
    }
    flow_depot_id = payload["flows"][0]["relief_center_id"] if payload["flows"] else depot_id
    mission = client.post(
        "/missions/",
        json={
            "zone_id": zone_id,
            "relief_center_id": flow_depot_id,
            "resources_payload": payload,
        },
    ).json()
    mission_id = mission["id"]

    client.patch(f"/missions/{mission_id}/status", json={"status": "Dispatched"})
    mid = client.get("/inventory/").json()
    food_mid = next(
        item for item in mid if item["category"] == "food" and item["warehouse"] == depot_name
    )
    assert food_mid["in_transit_quantity"] >= 0

    client.patch(f"/missions/{mission_id}/status", json={"status": "In Transit"})
    client.patch(f"/missions/{mission_id}/status", json={"status": "Delivered"})
    final = client.get("/inventory/").json()
    food_final = next(
        item for item in final if item["category"] == "food" and item["warehouse"] == depot_name
    )
    assert food_final["in_transit_quantity"] == 0
