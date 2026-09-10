"""SACHET CAP 1.2 early-warning ingestion (NDMA).

These records are alerts, not confirmed disaster impact. They are stored in
``ndma_alerts`` and are never auto-inserted into ``disaster_events``.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy.orm import Session

from app.config.settings import (
    HTTP_CONNECT_TIMEOUT,
    HTTP_READ_TIMEOUT,
    NDMA_PORTAL_URL,
    SACHET_CAP_URL,
    SACHET_POLYGON_URL,
    SACHET_RSS_URL,
)
from app.core.logger import logger
from app.models.ndma_alert import NdmaAlert

HTTP_TIMEOUT = httpx.Timeout(
    connect=HTTP_CONNECT_TIMEOUT,
    read=HTTP_READ_TIMEOUT,
    write=HTTP_CONNECT_TIMEOUT,
    pool=HTTP_CONNECT_TIMEOUT,
)
USER_AGENT = "DisasterResponse/1.0 (SACHET CAP client)"
CAP_NS = "urn:oasis:names:tc:emergency:cap:1.2"
PROMOTABLE_SEVERITIES = {"Extreme", "Severe"}
DEFAULT_MAX_CAP_FETCHES = 40


def _unavailable(message: str, *, portal_status: Any = None) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": "NDMA SACHET",
        "role": "early_warning",
        "portal_url": NDMA_PORTAL_URL,
        "portal_reachable": False,
        "portal_status": portal_status,
        "alert_count": 0,
        "alerts": [],
        "message": message,
    }


def _local_name(tag: str) -> str:
    return tag.split("}")[-1].split(":")[-1]


def _child(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    direct = parent.find(f"{{{CAP_NS}}}{name}")
    if direct is not None:
        return direct
    for node in parent:
        if _local_name(node.tag) == name:
            return node
    return None


def _text(parent: ET.Element | None, name: str) -> str | None:
    node = _child(parent, name)
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _http_get(
    url: str,
    *,
    etag: str | None = None,
    params: dict[str, str] | None = None,
) -> httpx.Response:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml, text/xml, */*"}
    if etag:
        headers["If-None-Match"] = etag
    return httpx.get(
        url,
        params=params,
        headers=headers,
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
    )


def parse_sachet_rss(xml_text: str) -> list[dict[str, str]]:
    """Return current alert identifiers from the India RSS feed."""
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for item in root.iter():
        if _local_name(item.tag) != "item":
            continue
        guid = None
        link = None
        title = None
        for child in item:
            name = _local_name(child.tag)
            if name == "guid" and child.text:
                guid = child.text.strip()
            elif name == "link" and child.text:
                link = child.text.strip()
            elif name == "title" and child.text:
                title = child.text.strip()
        identifier = guid
        if not identifier and link:
            identifier = parse_qs(urlparse(link).query).get("identifier", [None])[0]
        if identifier:
            items.append(
                {"identifier": identifier, "title": title or "", "link": link or ""}
            )
    return items


def _centroid_from_polygon(polygon: str) -> tuple[float | None, float | None]:
    points: list[tuple[float, float]] = []
    for pair in polygon.split():
        parts = pair.split(",")
        if len(parts) != 2:
            continue
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
        except ValueError:
            continue
        points.append((lat, lon))
    if not points:
        return None, None
    lat = sum(p[0] for p in points) / len(points)
    lon = sum(p[1] for p in points) / len(points)
    return lat, lon


def _centroid_from_circle(circle: str) -> tuple[float | None, float | None]:
    parts = circle.replace(" ", ",").split(",")
    if len(parts) < 2:
        return None, None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None, None


def parse_polygon_xml(xml_text: str) -> str | None:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    for node in root.iter():
        if _local_name(node.tag) == "polygon" and node.text and node.text.strip():
            return node.text.strip()
    return None


def parse_cap_alert(xml_text: str) -> dict[str, Any]:
    """Extract CAP 1.2 warning fields. Missing/odd structure yields None fields."""
    root = ET.fromstring(xml_text)
    info = _child(root, "info")
    if info is not None:
        for candidate in list(root):
            if _local_name(candidate.tag) != "info":
                continue
            language = _text(candidate, "language") or ""
            if language.lower().startswith("en"):
                info = candidate
                break

    area = _child(info, "area")
    polygon = _text(area, "polygon")
    circle = _text(area, "circle")
    polygon_url = None
    if info is not None:
        for parameter in info:
            if _local_name(parameter.tag) != "parameter":
                continue
            if (_text(parameter, "valueName") or "").strip().lower() == "polygon url":
                polygon_url = _text(parameter, "value")
                break

    latitude = longitude = None
    if polygon:
        latitude, longitude = _centroid_from_polygon(polygon)
    elif circle:
        latitude, longitude = _centroid_from_circle(circle)

    return {
        "cap_identifier": _text(root, "identifier"),
        "sender": _text(root, "sender"),
        "sent": _parse_dt(_text(root, "sent")),
        "msg_status": _text(root, "status"),
        "msg_type": _text(root, "msgType"),
        "category": _text(info, "category"),
        "event": _text(info, "event"),
        "urgency": _text(info, "urgency"),
        "severity": _text(info, "severity"),
        "certainty": _text(info, "certainty"),
        "headline": _text(info, "headline"),
        "description": _text(info, "description"),
        "instruction": _text(info, "instruction"),
        "area_description": _text(area, "areaDesc"),
        "area_polygon": polygon,
        "area_circle": circle,
        "polygon_url": polygon_url,
        "latitude": latitude,
        "longitude": longitude,
        "effective": _parse_dt(_text(info, "effective")),
        "onset": _parse_dt(_text(info, "onset")),
        "expires": _parse_dt(_text(info, "expires")),
    }


def _alert_row_status(expires: datetime | None, now: datetime) -> str:
    if expires is not None and expires < now:
        return "Expired"
    return "Active"


def _serialize_alert(row: NdmaAlert) -> dict[str, Any]:
    return {
        "id": row.id,
        "identifier": row.identifier,
        "cap_identifier": row.cap_identifier,
        "sender": row.sender,
        "event": row.event,
        "category": row.category,
        "severity": row.severity,
        "urgency": row.urgency,
        "certainty": row.certainty,
        "area_description": row.area_description,
        "headline": row.headline,
        "effective": row.effective.isoformat() if row.effective else None,
        "onset": row.onset.isoformat() if row.onset else None,
        "expires": row.expires.isoformat() if row.expires else None,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "has_polygon": bool(row.area_polygon),
        "has_circle": bool(row.area_circle),
        "status": row.status,
        "source": row.source,
    }


def _apply_parsed(row: NdmaAlert, parsed: dict[str, Any], *, etag: str | None) -> None:
    now = datetime.utcnow()
    row.cap_identifier = parsed.get("cap_identifier")
    row.etag = etag
    row.sender = parsed.get("sender")
    row.sent = parsed.get("sent")
    row.msg_status = parsed.get("msg_status")
    row.msg_type = parsed.get("msg_type")
    row.category = parsed.get("category")
    row.event = parsed.get("event")
    row.urgency = parsed.get("urgency")
    row.severity = parsed.get("severity")
    row.certainty = parsed.get("certainty")
    row.headline = parsed.get("headline")
    row.description = parsed.get("description")
    row.instruction = parsed.get("instruction")
    row.area_description = parsed.get("area_description")
    row.area_polygon = parsed.get("area_polygon") or row.area_polygon
    row.area_circle = parsed.get("area_circle")
    if parsed.get("latitude") is not None:
        row.latitude = parsed["latitude"]
        row.longitude = parsed["longitude"]
    row.effective = parsed.get("effective")
    row.onset = parsed.get("onset")
    row.expires = parsed.get("expires")
    row.status = _alert_row_status(row.expires, now)
    row.source = "NDMA SACHET"
    row.updated_at = now
    if row.fetched_at is None:
        row.fetched_at = now


def _maybe_fetch_polygon(parsed: dict[str, Any], identifier: str) -> None:
    if parsed.get("area_polygon"):
        return
    polygon_url = parsed.get("polygon_url") or SACHET_POLYGON_URL
    try:
        response = _http_get(polygon_url, params={"identifier": identifier})
        if response.status_code >= 400:
            return
        polygon = parse_polygon_xml(response.text)
        if not polygon:
            return
        parsed["area_polygon"] = polygon
        lat, lon = _centroid_from_polygon(polygon)
        parsed["latitude"] = lat
        parsed["longitude"] = lon
    except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
        logger.warning("SACHET polygon fetch failed for %s: %s", identifier, exc)


def fetch_ndma_events(
    db: Session | None = None,
    *,
    max_cap_fetches: int = DEFAULT_MAX_CAP_FETCHES,
) -> dict[str, Any]:
    """Poll SACHET RSS + CAP XML and upsert early-warning rows.

    Status values:
    - ``ok``: feed reachable and at least one alert listed or stored
    - ``no_alerts``: feed reachable but currently empty
    - ``unavailable``: network/parse failure (never raises)
    """
    try:
        rss_response = _http_get(SACHET_RSS_URL)
        rss_response.raise_for_status()
        items = parse_sachet_rss(rss_response.text)
    except httpx.HTTPError as exc:
        return _unavailable(
            f"SACHET RSS is unreachable: {exc}",
            portal_status=f"unreachable: {exc}",
        )
    except ET.ParseError as exc:
        return _unavailable(
            f"SACHET RSS was not valid XML: {exc}",
            portal_status=rss_response.status_code if "rss_response" in locals() else None,
        )

    if not items:
        return {
            "status": "no_alerts",
            "source": "NDMA SACHET",
            "role": "early_warning",
            "portal_url": NDMA_PORTAL_URL,
            "portal_reachable": True,
            "portal_status": rss_response.status_code,
            "alert_count": 0,
            "imported": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "alerts": [],
            "message": (
                "SACHET India RSS is reachable and currently lists zero alerts. "
                "This is not an unimplemented integration."
            ),
        }

    imported = updated = unchanged = skipped = 0
    cap_fetches = 0
    if db is None:
        return _unavailable(
            "Database session is required to persist SACHET alerts.",
            portal_status=rss_response.status_code,
        )

    existing = {
        row.identifier: row
        for row in db.query(NdmaAlert).filter(
            NdmaAlert.identifier.in_([item["identifier"] for item in items])
        )
    }

    for item in items:
        identifier = item["identifier"]
        row = existing.get(identifier)
        if cap_fetches >= max_cap_fetches and (row is None or not row.etag):
            skipped += 1
            continue
        try:
            response = _http_get(
                SACHET_CAP_URL,
                params={"identifier": identifier},
                etag=row.etag if row is not None else None,
            )
            cap_fetches += 1
            if response.status_code == 304 and row is not None:
                row.status = _alert_row_status(row.expires, datetime.utcnow())
                row.updated_at = datetime.utcnow()
                unchanged += 1
                continue
            if response.status_code >= 400:
                logger.warning(
                    "SACHET CAP fetch failed for %s: HTTP %s",
                    identifier,
                    response.status_code,
                )
                skipped += 1
                continue
            parsed = parse_cap_alert(response.text)
            _maybe_fetch_polygon(parsed, identifier)
            etag = response.headers.get("etag")
            if row is None:
                row = NdmaAlert(
                    identifier=identifier,
                    fetched_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status="Active",
                    source="NDMA SACHET",
                )
                db.add(row)
                existing[identifier] = row
                _apply_parsed(row, parsed, etag=etag)
                imported += 1
            else:
                _apply_parsed(row, parsed, etag=etag)
                updated += 1
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            logger.warning("SACHET CAP parse/fetch failed for %s: %s", identifier, exc)
            skipped += 1

    db.commit()

    stored = (
        db.query(NdmaAlert)
        .order_by(NdmaAlert.sent.desc().nulls_last(), NdmaAlert.id.desc())
        .limit(50)
        .all()
    )
    alerts = [_serialize_alert(row) for row in stored]
    promotion_candidates = [
        {
            "identifier": row["identifier"],
            "severity": row["severity"],
            "event": row["event"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
        }
        for row in alerts
        if (row.get("severity") or "") in PROMOTABLE_SEVERITIES
        and row.get("status") == "Active"
    ]

    return {
        "status": "ok",
        "source": "NDMA SACHET",
        "role": "early_warning",
        "portal_url": NDMA_PORTAL_URL,
        "portal_reachable": True,
        "portal_status": rss_response.status_code,
        "listed": len(items),
        "imported": imported,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "alert_count": len(alerts),
        "alerts": alerts,
        "promotion_candidates": promotion_candidates,
        "promotion_not_wired": True,
        "message": (
            "SACHET CAP alerts ingested as early warnings only. "
            "No disaster_events were created. High-severity Active alerts "
            "are listed in promotion_candidates for a later opt-in mapping "
            "to pending disaster_events (requires lat/lon centroid; SACHET "
            "has no casualty or affected-population fields)."
        ),
    }
