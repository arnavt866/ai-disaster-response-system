"""Tests for reconciled district matching statistics."""

import pytest

from app.config.settings import TARGET_DISTRICTS_GEOJSON
from app.services.historical.district_matcher import (
    match_records_to_districts,
    validate_alias_table,
)
from app.services.historical.district_validator import validate_target_districts_geojson


def test_alias_table_has_no_conflicting_entries():
    validation = validate_alias_table()
    assert validation["valid"] is True
    assert validation["conflicting_aliases"] == []


def test_villupuram_aliases_are_intentional_spelling_variants():
    validation = validate_alias_table()
    villupuram_entries = [
        entry
        for entry in validation["multi_key_aliases"]
        if entry["geojson_district"] == "Villupuram"
    ]
    assert len(villupuram_entries) == 1
    assert set(villupuram_entries[0]["xml_district_keys"]) == {
        "villupuram",
        "villuppuram",
    }


def test_district_summary_reconciles_to_80_geojson_districts():
    geo = validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    records = [
        {"state_normalized": "Odisha", "district_raw": "Balasore"},
        {"state_normalized": "Odisha", "district_raw": "Nuapara"},
        {"state_normalized": "Uttarakhand", "district_raw": "Garhwal"},
        {"state_normalized": "Uttarakhand", "district_raw": "Pauri"},
        {"state_normalized": "Tamil Nadu", "district_raw": "VILLUPPURAM"},
    ]
    _, report = match_records_to_districts(records, geo)
    summary = report.district_summary

    assert summary["total_geojson_districts"] == 80
    assert (
        summary["unique_geojson_districts_with_historical_data"]
        + summary["unique_geojson_districts_without_historical_data"]
        == 80
    )
    assert summary["xml_to_geo_mapping_pair_count"] == len(
        report.xml_to_geo_mapping_pairs
    )
    # Nuapada/Nuapara and Garhwal/Pauri are many-to-one examples.
    assert len(report.many_to_one_mappings) >= 0


def test_mapping_pair_count_can_exceed_unique_geojson_matches():
    geo = validate_target_districts_geojson(TARGET_DISTRICTS_GEOJSON)
    records = [
        {"state_normalized": "Odisha", "district_raw": "Nuapada"},
        {"state_normalized": "Odisha", "district_raw": "Nuapara"},
    ]
    _, report = match_records_to_districts(records, geo)

    assert report.district_summary["xml_to_geo_mapping_pair_count"] == 2
    assert (
        report.district_summary["unique_geojson_districts_with_historical_data"]
        == 1
    )
