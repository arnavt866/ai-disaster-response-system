"""Validation for the 80-district target-state GeoJSON dataset."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.historical.district_aliases import (
    EXPECTED_STATE_COUNTS,
    TARGET_STATES,
)
from app.services.historical.district_normalizer import normalize_token


@dataclass
class DistrictGeoJsonValidation:
    path: str
    valid: bool
    feature_count: int
    crs: str | None
    state_counts: dict[str, int] = field(default_factory=dict)
    districts_by_state: dict[str, list[str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "valid": self.valid,
            "feature_count": self.feature_count,
            "crs": self.crs,
            "state_counts": self.state_counts,
            "districts_by_state": self.districts_by_state,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _extract_crs(data: dict[str, Any]) -> str | None:
    crs = data.get("crs")
    if isinstance(crs, dict):
        props = crs.get("properties", {})
        return props.get("name") or str(crs)
    return None


def _is_wgs84_crs(crs_name: str | None) -> bool:
    if not crs_name:
        return False
    lowered = crs_name.lower()
    return any(
        token in lowered
        for token in ("crs84", "epsg::4326", "epsg:4326", "wgs 84", "wgs84")
    )


def validate_target_districts_geojson(path: Path) -> DistrictGeoJsonValidation:
    """
    Validate that the target-state GeoJSON exists and contains exactly
    80 districts across the three expected states.
    """
    result = DistrictGeoJsonValidation(
        path=str(path),
        valid=False,
        feature_count=0,
        crs=None,
    )

    if not path.exists():
        result.errors.append(f"Target districts GeoJSON not found: {path}")
        return result

    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    features = data.get("features", [])
    result.feature_count = len(features)
    result.crs = _extract_crs(data)

    if result.feature_count != 80:
        result.errors.append(
            f"Expected exactly 80 features, found {result.feature_count}."
        )

    if not _is_wgs84_crs(result.crs):
        result.warnings.append(
            f"CRS is not clearly WGS84/EPSG:4326/CRS84: {result.crs!r}."
        )

    districts_by_state: dict[str, list[str]] = {s: [] for s in TARGET_STATES}

    for index, feature in enumerate(features):
        props = feature.get("properties", {})
        state = props.get("state_name") or props.get("state")
        district = props.get("district") or props.get("ds_name")

        if not state or not district:
            result.errors.append(
                f"Feature {index}: missing state_name or district property."
            )
            continue

        if state not in TARGET_STATES:
            result.errors.append(
                f"Feature {index}: unexpected state {state!r}."
            )
            continue

        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in {
            "Polygon",
            "MultiPolygon",
        }:
            result.errors.append(
                f"Feature {index}: invalid or missing polygon geometry."
            )

        districts_by_state[state].append(str(district))

    for state, districts in districts_by_state.items():
        result.state_counts[state] = len(districts)
        expected = EXPECTED_STATE_COUNTS[state]
        if len(districts) != expected:
            result.errors.append(
                f"{state}: expected {expected} districts, found {len(districts)}."
            )

        # Duplicate district names within a state.
        normalized = [normalize_token(d) for d in districts]
        if len(normalized) != len(set(normalized)):
            result.errors.append(f"{state}: duplicate district names detected.")

        result.districts_by_state[state] = sorted(districts)

    result.valid = len(result.errors) == 0
    return result


def build_geo_district_lookup(
    validation: DistrictGeoJsonValidation,
) -> dict[str, dict[str, str]]:
    """Build {state: {normalized_district_key: canonical_name}} lookup."""
    lookup: dict[str, dict[str, str]] = {}
    for state, districts in validation.districts_by_state.items():
        lookup[state] = {
            normalize_token(name): name for name in districts
        }
    return lookup
