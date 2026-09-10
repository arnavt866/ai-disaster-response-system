"""Read-only GDACS-style zone advisory scoring (proximity + hazard-type match)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.disaster_zone import DisasterZone
from app.services.disaster_service import get_disaster_by_id
from app.services.optimization.routing_service import haversine_km

_FIXTURE_ZONE_MARKERS = ("M3 Test Zone", "Tracking Zone")

# Normalize common GDACS / DesInventar / zone type tokens for comparison.
_TYPE_ALIASES: dict[str, str] = {
    "eq": "earthquake",
    "earthquake": "earthquake",
    "fl": "flood",
    "flood": "flood",
    "tc": "cyclone",
    "cyclone": "cyclone",
    "tropical cyclone": "cyclone",
    "wf": "wildfire",
    "wildfire": "wildfire",
    "dr": "drought",
    "drought": "drought",
}

_SEVERITY_POINTS: dict[str, float] = {
    "critical": 40.0,
    "red": 40.0,
    "high": 30.0,
    "orange": 25.0,
    "moderate": 20.0,
    "medium": 20.0,
    "yellow": 15.0,
    "low": 10.0,
    "green": 5.0,
}


def _normalize_type(value: str | None) -> str:
    if not value:
        return "unknown"
    key = str(value).strip().lower()
    return _TYPE_ALIASES.get(key, key)


def _severity_points(severity: str | None) -> float:
    if not severity:
        return 10.0
    return _SEVERITY_POINTS.get(str(severity).strip().lower(), 10.0)


def _advisory_level(score: float) -> str:
    if score >= 70.0:
        return "Critical"
    if score >= 50.0:
        return "Elevated"
    if score >= 30.0:
        return "Advisory"
    return "Watch"


def score_zone_for_disaster(
    *,
    disaster_lat: float,
    disaster_lon: float,
    disaster_type: str,
    disaster_severity: str | None,
    zone: DisasterZone,
) -> dict[str, Any]:
    """Rule-based advisory score for one zone relative to a hazard point."""
    distance_km = round(
        haversine_km(disaster_lat, disaster_lon, zone.latitude, zone.longitude),
        2,
    )
    proximity_score = max(0.0, 100.0 - distance_km)

    event_type = _normalize_type(disaster_type)
    zone_type = _normalize_type(zone.disaster_type)
    if event_type == zone_type and event_type != "unknown":
        type_bonus = 30.0
        type_match = "exact"
    elif event_type != "unknown" and zone_type != "unknown" and (
        event_type in zone_type or zone_type in event_type
    ):
        type_bonus = 15.0
        type_match = "partial"
    else:
        type_bonus = 0.0
        type_match = "none"

    severity_score = _severity_points(disaster_severity)
    total_score = round(
        proximity_score * 0.5 + type_bonus + severity_score,
        1,
    )

    return {
        "zone_id": zone.id,
        "zone_name": zone.zone_name,
        "zone_type": zone.disaster_type,
        "zone_severity": zone.severity,
        "zone_status": zone.status,
        "distance_km": distance_km,
        "type_match": type_match,
        "advisory_score": total_score,
        "advisory_level": _advisory_level(total_score),
        "factors": {
            "proximity_score": round(proximity_score, 1),
            "type_bonus": type_bonus,
            "severity_score": severity_score,
        },
    }


def get_disaster_zone_advisory(
    db: Session,
    disaster_id: int,
    *,
    radius_km: float = 150.0,
    limit: int = 15,
) -> dict[str, Any]:
    """Score nearby active zones for a persisted disaster/GDACS event (read-only)."""
    disaster = get_disaster_by_id(db, disaster_id)
    if disaster is None:
        raise ValueError(f"Disaster {disaster_id} not found")

    zones = (
        db.query(DisasterZone)
        .filter(
            DisasterZone.status == "Active",
            *[
                ~DisasterZone.zone_name.ilike(f"%{marker}%")
                for marker in _FIXTURE_ZONE_MARKERS
            ],
        )
        .all()
    )

    scored: list[dict[str, Any]] = []
    for zone in zones:
        distance_km = haversine_km(
            disaster.latitude,
            disaster.longitude,
            zone.latitude,
            zone.longitude,
        )
        if distance_km > radius_km:
            continue
        scored.append(
            score_zone_for_disaster(
                disaster_lat=disaster.latitude,
                disaster_lon=disaster.longitude,
                disaster_type=disaster.disaster_type,
                disaster_severity=disaster.severity,
                zone=zone,
            )
        )

    scored.sort(key=lambda row: (-row["advisory_score"], row["distance_km"]))
    top = scored[:limit]

    return {
        "disaster_id": disaster.id,
        "event_id": disaster.event_id,
        "title": disaster.title,
        "disaster_type": disaster.disaster_type,
        "severity": disaster.severity,
        "source": disaster.source,
        "latitude": disaster.latitude,
        "longitude": disaster.longitude,
        "radius_km": radius_km,
        "zones_scored": len(scored),
        "advisories": top,
        "read_only": True,
        "note": (
            "Advisory cards are rule-based proximity/type scores for demo display. "
            "They do not create or modify disaster zones."
        ),
    }
