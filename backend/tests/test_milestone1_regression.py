"""Milestone-1 regression smoke tests — verify M2 did not break M1 routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"].lower()


def test_ndma_placeholder_still_works():
    response = client.get("/ndma/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Not Implemented"
    assert "portal_url" in body


def test_satellite_damage_endpoint_returns_unknown_damage_level():
    from unittest.mock import MagicMock, patch

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"features": []}
    with patch("app.services.geospatial.satellite_service.httpx.get", return_value=mock_response):
        response = client.get(
            "/satellite/damage",
            params={"latitude": 20.2, "longitude": 85.8},
        )
    assert response.status_code == 200
    assert response.json()["damage_level"] == "Unknown"


def test_gdacs_route_exists():
    response = client.get("/gdacs/import")
    # May fail on network but route must exist (not 404)
    assert response.status_code != 404


def test_usgs_route_exists():
    response = client.get("/usgs/import")
    assert response.status_code != 404


def test_grid_generate_requires_parameters():
    response = client.get("/grid/generate")
    assert response.status_code == 422


def test_zones_crud_routes_exist():
    # Route existence check — DB may not be available in test env.
    response = client.get("/zones/")
    assert response.status_code in {200, 500}


def test_satellite_placeholder_still_works():
    response = client.get("/satellite/nearby", params={"latitude": 20.0, "longitude": 85.0})
    assert response.status_code in {200, 503}
