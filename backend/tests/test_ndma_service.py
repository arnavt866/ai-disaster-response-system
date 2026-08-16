"""NDMA placeholder service tests."""

from unittest.mock import MagicMock, patch

import httpx

from app.services.ndma_service import fetch_ndma_events


def test_ndma_returns_not_implemented_status():
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("app.services.ndma_service.httpx.get", return_value=mock_response):
        result = fetch_ndma_events()
    assert result["status"] == "Not Implemented"
    assert result["portal_reachable"] is True


def test_ndma_portal_unreachable_still_returns_safe_payload():
    with patch("app.services.ndma_service.httpx.get", side_effect=httpx.HTTPError("timeout")):
        result = fetch_ndma_events()
    assert result["status"] == "Not Implemented"
    assert result["portal_reachable"] is False
