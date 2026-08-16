"""Match normalized historical records to target-state GeoJSON districts."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.services.historical.district_aliases import DISTRICT_ALIASES
from app.services.historical.district_normalizer import (
    normalize_token,
    resolve_district_with_geojson,
)
from app.services.historical.district_validator import (
    DistrictGeoJsonValidation,
    build_geo_district_lookup,
)


@dataclass
class DistrictMatchingReport:
    # Reconciled summary counts (see district_summary).
    district_summary: dict[str, Any] = field(default_factory=dict)
    # One row per unique (state, xml_district, geojson_district) mapping observed in data.
    xml_to_geo_mapping_pairs: list[dict[str, Any]] = field(default_factory=list)
    unmatched_historical_districts: list[dict[str, Any]] = field(default_factory=list)
    unmatched_geojson_districts: list[dict[str, Any]] = field(default_factory=list)
    ambiguous_matches: list[dict[str, Any]] = field(default_factory=list)
    alias_mappings_used: list[dict[str, Any]] = field(default_factory=list)
    alias_validation: dict[str, Any] = field(default_factory=dict)
    many_to_one_mappings: list[dict[str, Any]] = field(default_factory=list)
    match_counts_by_state: dict[str, dict[str, int]] = field(default_factory=dict)
    record_match_summary: dict[str, int] = field(default_factory=dict)

    # Backward-compatible alias for older report consumers.
    @property
    def matched_districts(self) -> list[dict[str, Any]]:
        return self.xml_to_geo_mapping_pairs

    def to_dict(self) -> dict[str, Any]:
        return {
            "district_summary": self.district_summary,
            "xml_to_geo_mapping_pairs": self.xml_to_geo_mapping_pairs,
            "matched_districts": self.xml_to_geo_mapping_pairs,
            "unmatched_historical_districts": self.unmatched_historical_districts,
            "unmatched_geojson_districts": self.unmatched_geojson_districts,
            "ambiguous_matches": self.ambiguous_matches,
            "alias_mappings_used": self.alias_mappings_used,
            "alias_validation": self.alias_validation,
            "many_to_one_mappings": self.many_to_one_mappings,
            "match_counts_by_state": self.match_counts_by_state,
            "record_match_summary": self.record_match_summary,
        }


def _alias_mapping_entries() -> list[dict[str, str]]:
    entries = []
    for (state, xml_key), geo_name in sorted(DISTRICT_ALIASES.items()):
        entries.append(
            {
                "state": state,
                "xml_district_key": xml_key,
                "geojson_district": geo_name,
            }
        )
    return entries


def validate_alias_table() -> dict[str, Any]:
    """
    Inspect the static alias table for duplicate or suspicious entries.

    Multiple XML keys mapping to the same GeoJSON district is expected when
    historical data uses alternate spellings (e.g. villupuram / villuppuram).
    """
    by_geo: dict[tuple[str, str], list[str]] = defaultdict(list)
    for (state, xml_key), geo_name in DISTRICT_ALIASES.items():
        by_geo[(state, geo_name)].append(xml_key)

    multi_key_aliases = [
        {
            "state": state,
            "geojson_district": geo_name,
            "xml_district_keys": sorted(keys),
            "note": (
                "Multiple XML spellings intentionally map to one GeoJSON district."
            ),
        }
        for (state, geo_name), keys in sorted(by_geo.items())
        if len(keys) > 1
    ]

    # True duplicates: same (state, xml_key) with different geo targets.
    reverse: dict[tuple[str, str], set[str]] = defaultdict(set)
    for (state, xml_key), geo_name in DISTRICT_ALIASES.items():
        reverse[(state, xml_key)].add(geo_name)

    conflicting_aliases = [
        {
            "state": state,
            "xml_district_key": xml_key,
            "geojson_districts": sorted(geo_names),
        }
        for (state, xml_key), geo_names in sorted(reverse.items())
        if len(geo_names) > 1
    ]

    return {
        "total_alias_entries": len(DISTRICT_ALIASES),
        "multi_key_aliases": multi_key_aliases,
        "conflicting_aliases": conflicting_aliases,
        "valid": len(conflicting_aliases) == 0,
    }


def _build_district_summary(
    geo_validation: DistrictGeoJsonValidation,
    matched_pairs: set[tuple[str, str, str]],
    historical_districts_seen: dict[tuple[str, str], int],
    matched_historical: set[tuple[str, str]],
    updated_records: list[dict[str, Any]],
    unmatched_geojson: list[dict[str, Any]],
    many_to_one: list[dict[str, Any]],
) -> dict[str, Any]:
    total_geojson = sum(
        len(districts) for districts in geo_validation.districts_by_state.values()
    )
    unique_geo_with_data = len({(s, g) for s, _, g in matched_pairs})
    unique_geo_without_data = len(unmatched_geojson)
    unique_xml_names = len(historical_districts_seen)
    matched_records = sum(
        1 for record in updated_records if record.get("district_normalized")
    )
    unmatched_records = len(updated_records) - matched_records

    reconciliation_passed = (
        unique_geo_with_data + unique_geo_without_data == total_geojson
    )

    return {
        "total_geojson_districts": total_geojson,
        "unique_geojson_districts_with_historical_data": unique_geo_with_data,
        "unique_geojson_districts_without_historical_data": unique_geo_without_data,
        "unique_historical_xml_district_names": unique_xml_names,
        "xml_to_geo_mapping_pair_count": len(matched_pairs),
        "matched_historical_xml_district_names": len(matched_historical),
        "unmatched_historical_xml_district_names": unique_xml_names
        - len(matched_historical),
        "matched_records": matched_records,
        "unmatched_records": unmatched_records,
        "reconciliation_check": (
            f"{unique_geo_with_data} + {unique_geo_without_data} = {total_geojson}"
        ),
        "reconciliation_check_passed": reconciliation_passed,
        "counting_note": (
            "xml_to_geo_mapping_pair_count can exceed "
            "unique_geojson_districts_with_historical_data when multiple "
            "historical XML district spellings map to the same GeoJSON district."
        ),
    }


def match_records_to_districts(
    records: list[dict[str, Any]],
    geo_validation: DistrictGeoJsonValidation,
) -> tuple[list[dict[str, Any]], DistrictMatchingReport]:
    """
    Resolve district_normalized for each record and produce a matching report.

    Returns (updated_records, report).
    """
    report = DistrictMatchingReport()
    report.alias_mappings_used = _alias_mapping_entries()
    report.alias_validation = validate_alias_table()

    geo_lookup = build_geo_district_lookup(geo_validation)
    matched_pairs: set[tuple[str, str, str]] = set()
    historical_districts_seen: dict[tuple[str, str], int] = Counter()
    matched_historical: set[tuple[str, str]] = set()

    updated_records: list[dict[str, Any]] = []

    for record in records:
        state = record.get("state_normalized")
        district_raw = record.get("district_raw", "")
        key = (state or "", normalize_token(district_raw))
        if state and district_raw:
            historical_districts_seen[key] += 1

        matched_district = None
        match_method = "unmatched"

        if state:
            matched_district, match_method = resolve_district_with_geojson(
                state,
                district_raw,
                geo_lookup,
            )

        updated = dict(record)
        updated["district_normalized"] = matched_district
        updated["district_match_method"] = match_method
        updated_records.append(updated)

        if state and district_raw:
            if matched_district:
                matched_historical.add(key)
                matched_pairs.add((state, district_raw, matched_district))
            report.record_match_summary[match_method] = (
                report.record_match_summary.get(match_method, 0) + 1
            )

    # Mapping-pair inventory (one row per unique XML spelling → GeoJSON district).
    for state, raw_name, geo_name in sorted(matched_pairs):
        report.xml_to_geo_mapping_pairs.append(
            {
                "state": state,
                "xml_district": raw_name,
                "geojson_district": geo_name,
                "record_count": historical_districts_seen.get(
                    (state, normalize_token(raw_name)),
                    0,
                ),
            }
        )

    # Many-to-one: multiple XML district names → same GeoJSON district.
    by_geo: dict[tuple[str, str], list[str]] = defaultdict(list)
    for state, raw_name, geo_name in matched_pairs:
        by_geo[(state, geo_name)].append(raw_name)

    for (state, geo_name), xml_names in sorted(by_geo.items()):
        if len(xml_names) > 1:
            report.many_to_one_mappings.append(
                {
                    "state": state,
                    "geojson_district": geo_name,
                    "xml_districts": sorted(xml_names),
                    "explanation": (
                        "Multiple historical XML spellings resolve to one "
                        "GeoJSON district."
                    ),
                }
            )

    # Unmatched historical districts.
    for (state, district_key), count in sorted(historical_districts_seen.items()):
        if (state, district_key) not in matched_historical:
            report.unmatched_historical_districts.append(
                {
                    "state": state,
                    "district_raw_key": district_key,
                    "record_count": count,
                }
            )

    # Unmatched GeoJSON districts.
    matched_geo_by_state: dict[str, set[str]] = defaultdict(set)
    for state, _, geo_name in matched_pairs:
        matched_geo_by_state[state].add(geo_name)

    for state, districts in geo_validation.districts_by_state.items():
        for district in districts:
            if district not in matched_geo_by_state.get(state, set()):
                report.unmatched_geojson_districts.append(
                    {
                        "state": state,
                        "geojson_district": district,
                        "reason": (
                            "No historical XML records mapped to this district. "
                            "May be a post-reorganization district."
                        ),
                    }
                )

    report.district_summary = _build_district_summary(
        geo_validation=geo_validation,
        matched_pairs=matched_pairs,
        historical_districts_seen=historical_districts_seen,
        matched_historical=matched_historical,
        updated_records=updated_records,
        unmatched_geojson=report.unmatched_geojson_districts,
        many_to_one=report.many_to_one_mappings,
    )

    # Per-state summary.
    for state in geo_validation.districts_by_state:
        xml_districts = {
            key[1] for key in historical_districts_seen if key[0] == state
        }
        unique_geo_matched = len(matched_geo_by_state.get(state, set()))
        report.match_counts_by_state[state] = {
            "unique_historical_xml_district_names": len(xml_districts),
            "geojson_districts": len(geo_validation.districts_by_state[state]),
            "unique_geojson_districts_with_historical_data": unique_geo_matched,
            "xml_to_geo_mapping_pairs": len(
                [
                    pair
                    for pair in report.xml_to_geo_mapping_pairs
                    if pair["state"] == state
                ]
            ),
            "unmatched_historical_xml_district_names": len(
                [
                    entry
                    for entry in report.unmatched_historical_districts
                    if entry["state"] == state
                ]
            ),
            "unmatched_geojson_districts": len(
                [
                    entry
                    for entry in report.unmatched_geojson_districts
                    if entry["state"] == state
                ]
            ),
        }

    return updated_records, report
