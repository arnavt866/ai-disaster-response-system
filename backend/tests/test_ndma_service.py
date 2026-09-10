"""SACHET CAP / RSS ingestion tests — no live NDMA network calls."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.ndma_service import (
    fetch_ndma_events,
    parse_cap_alert,
    parse_polygon_xml,
    parse_sachet_rss,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
CAP_XML = (FIXTURE_DIR / "sachet_cap_sample.xml").read_text(encoding="utf-8")
client = TestClient(app)

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>All India: CAP Disaster Alert Feeds</title>
    <item>
      <title>Thunderstorm likely over Darjeeling district.</title>
      <link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=test-id-001</link>
      <guid isPermaLink="false">test-id-001</guid>
    </item>
  </channel>
</rss>
"""

EMPTY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>All India</title></channel></rss>
"""

POLYGON_XML = """<?xml version="1.0"?>
<alert>
  <identifier>IN-TEST-ALERT-001</identifier>
  <polygon>27.0,88.0 27.2,88.0 27.2,88.4 27.0,88.4 27.0,88.0</polygon>
</alert>
"""


def _response(status_code: int, text: str = "", etag: str | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.headers = {"etag": etag} if etag else {}
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=response,
        )
    else:
        response.raise_for_status.return_value = None
    return response


def test_parse_cap_alert_extracts_warning_fields():
    parsed = parse_cap_alert(CAP_XML)
    assert parsed["cap_identifier"] == "IN-TEST-ALERT-001"
    assert parsed["event"] == "Moderate Thunderstorms with surface wind"
    assert parsed["severity"] == "Severe"
    assert parsed["urgency"] == "Expected"
    assert parsed["certainty"] == "Likely"
    assert parsed["area_description"] == "Darjiling district of West Bengal"
    assert parsed["effective"] is not None
    assert parsed["onset"] is not None
    assert parsed["expires"] is not None
    assert parsed["area_circle"].startswith("27.04,88.26")
    assert parsed["latitude"] == 27.04
    assert parsed["longitude"] == 88.26


def test_parse_rss_identifiers_and_polygon_xml():
    items = parse_sachet_rss(RSS_XML)
    assert items[0]["identifier"] == "test-id-001"
    polygon = parse_polygon_xml(POLYGON_XML)
    assert polygon.startswith("27.0,88.0")


def test_fetch_ndma_events_persists_parsed_alert(_db_savepoint_isolation):
    def fake_get(url, *, etag=None, params=None):
        url = str(url)
        if "rss_india" in url:
            return _response(200, RSS_XML)
        if "FetchPolygonXMLFile" in url:
            return _response(200, POLYGON_XML)
        return _response(200, CAP_XML, etag='"etag-1"')

    with patch("app.services.ndma_service._http_get", side_effect=fake_get):
        result = fetch_ndma_events(_db_savepoint_isolation)

    assert result["status"] == "ok"
    assert result["imported"] == 1
    assert result["alerts"]
    alert = next(row for row in result["alerts"] if row["identifier"] == "test-id-001")
    assert alert["event"] == "Moderate Thunderstorms with surface wind"
    assert alert["severity"] == "Severe"
    assert alert["urgency"] == "Expected"
    assert alert["area_description"] == "Darjiling district of West Bengal"
    assert alert["status"] in {"Active", "Expired"}
    assert result["promotion_not_wired"] is True


def test_etag_304_skips_reprocessing(_db_savepoint_isolation):
    calls = {"cap": 0}

    def fake_get(url, *, etag=None, params=None):
        url = str(url)
        if "rss_india" in url:
            return _response(200, RSS_XML)
        if "FetchPolygonXMLFile" in url:
            return _response(200, POLYGON_XML)
        calls["cap"] += 1
        if etag == '"etag-1"':
            return _response(304, "", etag='"etag-1"')
        return _response(200, CAP_XML, etag='"etag-1"')

    with patch("app.services.ndma_service._http_get", side_effect=fake_get):
        first = fetch_ndma_events(_db_savepoint_isolation)
        second = fetch_ndma_events(_db_savepoint_isolation)

    assert first["imported"] == 1
    assert second["unchanged"] == 1
    assert second["imported"] == 0
    assert calls["cap"] == 2


def test_empty_rss_is_no_alerts_not_unimplemented(_db_savepoint_isolation):
    with patch(
        "app.services.ndma_service._http_get",
        return_value=_response(200, EMPTY_RSS),
    ):
        result = fetch_ndma_events(_db_savepoint_isolation)
    assert result["status"] == "no_alerts"
    assert result["status"] != "Not Implemented"
    assert result["alert_count"] == 0


def test_unreachable_sachet_returns_unavailable(_db_savepoint_isolation):
    with patch(
        "app.services.ndma_service._http_get",
        side_effect=httpx.ConnectError("timeout"),
    ):
        result = fetch_ndma_events(_db_savepoint_isolation)
    assert result["status"] == "unavailable"
    assert result["portal_reachable"] is False
    assert result["alerts"] == []


def test_ndma_route_uses_ingested_shape():
    payload = {
        "status": "no_alerts",
        "source": "NDMA SACHET",
        "portal_url": "https://sachet.ndma.gov.in/",
        "alerts": [],
        "alert_count": 0,
    }
    with patch("app.api.ndma_routes.fetch_ndma_events", return_value=payload):
        response = client.get("/ndma/")
    assert response.status_code == 200
    assert response.json()["status"] == "no_alerts"
