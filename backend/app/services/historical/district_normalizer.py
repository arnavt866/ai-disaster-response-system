"""Deterministic state and district name normalization."""

from __future__ import annotations

import re
import unicodedata

from app.services.historical.district_aliases import (
    DISTRICT_ALIASES,
    STATE_ALIASES,
    TARGET_STATES,
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_token(value: str | None) -> str:
    """Lowercase, strip accents, collapse punctuation to spaces."""
    if not value:
        return ""

    text = unicodedata.normalize("NFKD", value.strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())


def title_case_district(value: str) -> str:
    """Title-case a district name while preserving short uppercase tokens."""
    parts = value.split()
    result: list[str] = []
    for part in parts:
        if part.isupper() and len(part) <= 3:
            result.append(part)
        else:
            result.append(part.capitalize())
    return " ".join(result)


def normalize_state_name(raw_state: str | None) -> str | None:
    """Map a raw XML state name to a canonical target-state name."""
    key = normalize_token(raw_state)
    if not key:
        return None

    canonical = STATE_ALIASES.get(key)
    if canonical:
        return canonical

    # Already canonical?
    for state in TARGET_STATES:
        if normalize_token(state) == key:
            return state

    return None


def normalize_district_name(
    canonical_state: str,
    raw_district: str | None,
) -> str | None:
    """
    Map a raw XML district (name1) to a canonical GeoJSON district name.

    Resolution order:
    1. Explicit alias table
    2. Case-insensitive exact match against known GeoJSON districts
       (caller provides geo_districts lookup when available)
  3. Title-cased raw value as fallback candidate
    """
    key = normalize_token(raw_district)
    if not key or canonical_state not in TARGET_STATES:
        return None

    alias = DISTRICT_ALIASES.get((canonical_state, key))
    if alias:
        return alias

    if raw_district and raw_district.strip():
        return title_case_district(raw_district.strip())

    return None


def resolve_district_with_geojson(
    canonical_state: str,
    raw_district: str | None,
    geo_districts_by_state: dict[str, dict[str, str]],
) -> tuple[str | None, str]:
    """
    Resolve a district name against the GeoJSON district inventory.

    Returns (matched_geojson_district, match_method).
    match_method is one of: alias, exact, case_insensitive, unmatched.
    """
    key = normalize_token(raw_district)
    if not key:
        return None, "unmatched"

    alias = DISTRICT_ALIASES.get((canonical_state, key))
    if alias:
        lookup = geo_districts_by_state.get(canonical_state, {})
        if alias in lookup.values() or alias in lookup:
            return alias, "alias"

    lookup = geo_districts_by_state.get(canonical_state, {})
    if not lookup:
        candidate = normalize_district_name(canonical_state, raw_district)
        return candidate, "unmatched"

    if key in lookup:
        return lookup[key], "case_insensitive"

    candidate = normalize_district_name(canonical_state, raw_district)
    if candidate and candidate in lookup.values():
        return candidate, "exact"

    for geo_key, geo_name in lookup.items():
        if geo_key == key:
            return geo_name, "case_insensitive"

    return None, "unmatched"
