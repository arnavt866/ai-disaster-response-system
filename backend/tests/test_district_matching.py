"""Tests for district normalization and matching."""

import pytest

from app.config.settings import TARGET_DISTRICTS_GEOJSON
from app.services.historical.district_aliases import EXPECTED_STATE_COUNTS
from app.services.historical.district_matcher import match_records_to_districts
from app.services.historical.district_normalizer import (
    normalize_state_name,
    normalize_token,
    resolve_district_with_geojson,
)
from app.services.historical.district_validator import (
    build_geo_district_lookup,
    validate_target_districts_geojson,
)
from app.services.historical.historical_normalizer import (
    safe_int,
    normalize_disaster_type,
    parse_event_date,
)


def test_target_geojson_has_80_districts():
    result = validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    assert result.valid, result.errors
    assert result.feature_count == 80
    for state, expected in EXPECTED_STATE_COUNTS.items():
        assert result.state_counts[state] == expected


def test_normalize_state_orissa_to_odisha():
    assert normalize_state_name("Orissa") == "Odisha"


def test_normalize_token_strips_punctuation():
    assert normalize_token("  THIRUVANNAMALAI ") == "thiruvannamalai"


def test_odisha_district_aliases():
    lookup = build_geo_district_lookup(
        validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    )
    matched, method = resolve_district_with_geojson(
        "Odisha", "Balasore", lookup
    )
    assert matched == "Baleshwar"
    assert method == "alias"


def test_tamil_nadu_case_insensitive_match():
    lookup = build_geo_district_lookup(
        validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    )
    matched, method = resolve_district_with_geojson(
        "Tamil Nadu", "COIMBATORE", lookup
    )
    assert matched == "Coimbatore"
    assert method == "case_insensitive"


def test_uttarakhand_hardwar_alias():
    lookup = build_geo_district_lookup(
        validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    )
    matched, method = resolve_district_with_geojson(
        "Uttarakhand", "Hardwar", lookup
    )
    assert matched == "Haridwar"
    assert method == "alias"


def test_safe_int_handles_empty_and_invalid():
    assert safe_int("") is None
    assert safe_int("abc") is None
    assert safe_int("360") == 360


def test_parse_event_date_valid():
    event_date, year, month, day = parse_event_date("1971", "6", "26")
    assert str(event_date) == "1971-06-26"
    assert year == 1971 and month == 6 and day == 26


def test_normalize_disaster_type():
    assert normalize_disaster_type("FLOOD") == "Flood"
    assert normalize_disaster_type("Road Accident") == "Road Accident"


def test_match_records_produces_report():
    geo = validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    records = [
        {
            "state_normalized": "Odisha",
            "district_raw": "Balasore",
        },
        {
            "state_normalized": "Odisha",
            "district_raw": "UnknownDistrict",
        },
    ]
    updated, report = match_records_to_districts(records, geo)
    assert updated[0]["district_normalized"] == "Baleshwar"
    assert updated[1]["district_normalized"] is None
    assert len(report.matched_districts) >= 1
    assert len(report.unmatched_historical_districts) >= 1
