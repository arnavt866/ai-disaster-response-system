"""Pagination for GET /disasters/ and GET /zones/."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_disasters_list_default_pagination():
    response = client.get("/disasters/")
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"total", "offset", "limit", "records"}
    assert body["offset"] == 0
    assert body["limit"] == 100
    assert body["total"] >= len(body["records"])
    assert len(body["records"]) <= 100


def test_disasters_list_offset_limit():
    first = client.get("/disasters/", params={"offset": 0, "limit": 2})
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["records"]) <= 2
    if first_body["total"] > 2:
        second = client.get("/disasters/", params={"offset": 2, "limit": 2})
        assert second.status_code == 200
        second_ids = [row["id"] for row in second.json()["records"]]
        first_ids = [row["id"] for row in first_body["records"]]
        assert first_ids != second_ids


def test_disasters_list_rejects_invalid_limit():
    response = client.get("/disasters/", params={"limit": 0})
    assert response.status_code == 422


def test_zones_list_default_pagination():
    response = client.get("/zones/")
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"total", "offset", "limit", "records"}
    assert body["offset"] == 0
    assert body["limit"] == 100
    assert body["total"] >= len(body["records"])
    assert len(body["records"]) <= 100


def test_zones_list_offset_limit():
    created = client.post(
        "/zones/",
        json={
            "zone_name": "Pagination Zone",
            "disaster_type": "Flood",
            "severity": "High",
            "latitude": 20.2961,
            "longitude": 85.8245,
            "affected_population": 10,
            "status": "Active",
            "operational_priority": "High",
        },
    )
    assert created.status_code == 200

    page = client.get("/zones/", params={"offset": 0, "limit": 1})
    assert page.status_code == 200
    body = page.json()
    assert body["total"] >= 1
    assert len(body["records"]) == 1
    assert "id" in body["records"][0]


def test_zones_list_rejects_negative_offset():
    response = client.get("/zones/", params={"offset": -1})
    assert response.status_code == 422


def test_zone_response_includes_vulnerability_and_priority_fields():
    created = client.post(
        "/zones/",
        json={
            "zone_name": "Schema Fields Zone",
            "disaster_type": "Flood",
            "severity": "High",
            "latitude": 20.2961,
            "longitude": 85.8245,
            "affected_population": 10,
            "status": "Active",
            "operational_priority": "Critical",
        },
    )
    assert created.status_code == 200
    body = created.json()
    zone_id = body["id"]
    assert body["operational_priority"] == "Critical"
    assert "vulnerability_data_available" in body
    assert "elderly_share" in body
    assert "child_share" in body

    updated = client.put(
        f"/zones/{zone_id}",
        json={
            "zone_name": "Schema Fields Zone",
            "disaster_type": "Flood",
            "severity": "High",
            "latitude": 20.2961,
            "longitude": 85.8245,
            "affected_population": 10,
            "status": "Active",
            "operational_priority": "Low",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["operational_priority"] == "Low"
