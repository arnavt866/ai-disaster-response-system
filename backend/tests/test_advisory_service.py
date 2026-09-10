"""Tests for read-only disaster zone advisory scoring."""

from types import SimpleNamespace

from app.services.advisory_service import (
    _advisory_level,
    score_zone_for_disaster,
)


def test_advisory_level_thresholds():
    assert _advisory_level(75) == "Critical"
    assert _advisory_level(55) == "Elevated"
    assert _advisory_level(35) == "Advisory"
    assert _advisory_level(10) == "Watch"


def test_score_zone_exact_type_match_boosts_score():
    zone = SimpleNamespace(
        id=1,
        zone_name="Chennai Flood Zone",
        disaster_type="FL",
        severity="High",
        status="Active",
        latitude=13.10,
        longitude=80.28,
    )
    result = score_zone_for_disaster(
        disaster_lat=13.0827,
        disaster_lon=80.2707,
        disaster_type="FL",
        disaster_severity="High",
        zone=zone,
    )
    assert result["type_match"] == "exact"
    assert result["advisory_level"] in {"Elevated", "Critical", "Advisory"}
    assert result["distance_km"] < 10
