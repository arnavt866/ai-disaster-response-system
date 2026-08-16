"""Satellite and Overpass service tests (mocked external APIs)."""

from unittest.mock import MagicMock, patch

import httpx

from app.services.geospatial.satellite_service import (
    get_damage_estimation,
    get_nearby_facilities,
)


def test_nearby_facilities_overpass_failure_returns_unavailable():
    with patch("app.services.geospatial.satellite_service.httpx.post") as mock_post:
        mock_post.side_effect = httpx.HTTPError("network down")
        result = get_nearby_facilities(20.0, 85.0)
    assert result["status"] == "Service Unavailable"
    assert result["count"] == 0


def test_nearby_facilities_overpass_success():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "elements": [
            {
                "lat": 20.0,
                "lon": 85.0,
                "tags": {"name": "City Hospital", "amenity": "hospital"},
            }
        ]
    }
    with patch("app.services.geospatial.satellite_service.httpx.post", return_value=mock_response):
        result = get_nearby_facilities(20.0, 85.0)
    assert result["status"] == "Success"
    assert result["count"] == 1


def test_damage_estimation_returns_scene_metadata_without_damage_score():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "features": [
            {
                "id": "S2A_TEST",
                "properties": {
                    "datetime": "2026-08-11T05:03:20Z",
                    "eo:cloud_cover": 12.5,
                    "platform": "sentinel-2a",
                },
            }
        ]
    }
    with patch("app.services.geospatial.satellite_service.httpx.get", return_value=mock_response):
        result = get_damage_estimation(20.2, 85.8)
    assert result["damage_level"] == "Unknown"
    assert result["imagery_available"] is True
    assert result["scene_metadata"]["scene_count"] == 1


def test_damage_estimation_stac_failure_falls_back_safely():
    with patch("app.services.geospatial.satellite_service.httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("timeout")
        result = get_damage_estimation(20.2, 85.8)
    assert result["damage_level"] == "Unknown"
    assert result["imagery_available"] is False
    assert result["status"] == "Satellite catalog unavailable"
