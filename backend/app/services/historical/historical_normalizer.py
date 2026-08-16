"""Normalize raw DESINVENTAR records into a consistent historical schema."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.historical.desinventar_parser import RawDisasterRecord
from app.services.historical.district_normalizer import (
    normalize_state_name,
    normalize_token,
)

# Canonical disaster-type mapping (lowercase key -> normalized label).
DISASTER_TYPE_ALIASES: dict[str, str] = {
    "flood": "Flood",
    "flash flood": "Flood",
    "cyclone": "Cyclone",
    "earthquake": "Earthquake",
    "landslide": "Landslide",
    "cloud burst": "Cloud Burst",
    "rains": "Rains",
    "drought": "Drought",
    "fire": "Fire",
    "forest fire": "Forest Fire",
    "epidemic": "Epidemic",
    "heat wave": "Heat Wave",
    "hailstorm": "Hailstorm",
    "storm": "Storm",
    "electric storm": "Electric Storm",
    "lighting": "Lightning",
    "lightning": "Lightning",
    "accident": "Accident",
    "road accident": "Road Accident",
    "structure": "Structure Collapse",
    "snowfall": "Snowfall",
    "alluvion": "Alluvion",
    "avalanche": "Avalanche",
    "eruption": "Eruption",
    "explosion": "Explosion",
    "boat capsize": "Boat Capsize",
}

# Output feature columns for the normalized historical dataset (no proxy targets).
NORMALIZED_FEATURE_COLUMNS: tuple[str, ...] = (
    "record_id",
    "source_file",
    "source_state",
    "state_raw",
    "state_normalized",
    "district_raw",
    "district_normalized",
    "sub_district_raw",
    "disaster_type_raw",
    "disaster_type_normalized",
    "event_date",
    "event_year",
    "event_month",
    "event_day",
    "deaths",
    "injuries",
    "missing_persons",
    "affected_population",
    "evacuated_population",
    "houses_destroyed",
    "houses_damaged",
    "affected_families",
    "relocated_population",
    "hospitals_affected",
    "schools_affected",
    "agricultural_hectares",
    "livestock_heads",
    "road_damage_km",
    "duration_days",
    "economic_loss_local",
    "economic_loss_usd",
    "location_description",
    "data_source_notes",
    "latitude",
    "longitude",
    "sector_relief",
    "sector_health",
    "sector_education",
    "sector_agriculture",
    "sector_industry",
    "sector_water",
    "sector_sewer",
    "sector_energy",
    "sector_communications",
    "sector_transport",
)


def safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def safe_flag(value: str | None) -> int | None:
    parsed = safe_int(value)
    if parsed is None:
        return None
    return 1 if parsed else 0


def normalize_disaster_type(raw_type: str | None) -> str | None:
    if not raw_type or not raw_type.strip():
        return None
    key = normalize_token(raw_type)
    return DISASTER_TYPE_ALIASES.get(key, raw_type.strip().title())


def parse_event_date(
    year: str | None,
    month: str | None,
    day: str | None,
) -> tuple[date | None, int | None, int | None, int | None]:
    year_i = safe_int(year)
    month_i = safe_int(month)
    day_i = safe_int(day)

    if year_i is None:
        return None, None, month_i, day_i

    if month_i is None or not 1 <= month_i <= 12:
        return None, year_i, month_i, day_i

    if day_i is None or not 1 <= day_i <= 31:
        return None, year_i, month_i, day_i

    try:
        return date(year_i, month_i, day_i), year_i, month_i, day_i
    except ValueError:
        return None, year_i, month_i, day_i


def normalize_record(raw: RawDisasterRecord) -> dict[str, Any]:
    """Transform a raw XML record into a normalized historical feature row."""
    fields = raw.fields
    state_raw = fields.get("name0", "")
    district_raw = fields.get("name1", "")
    sub_district_raw = fields.get("name2", "")

    state_normalized = normalize_state_name(state_raw)
    event_date, event_year, event_month, event_day = parse_event_date(
        fields.get("fechano"),
        fields.get("fechames"),
        fields.get("fechadia"),
    )

    serial = fields.get("serial", "")
    record_id = f"{raw.source_state}:{serial}" if serial else f"{raw.source_state}:unknown"

    return {
        "record_id": record_id,
        "source_file": raw.source_file,
        "source_state": raw.source_state,
        "state_raw": state_raw,
        "state_normalized": state_normalized,
        "district_raw": district_raw,
        "district_normalized": None,  # resolved in district matcher
        "sub_district_raw": sub_district_raw,
        "disaster_type_raw": fields.get("evento", ""),
        "disaster_type_normalized": normalize_disaster_type(fields.get("evento")),
        "event_date": event_date.isoformat() if event_date else None,
        "event_year": event_year,
        "event_month": event_month,
        "event_day": event_day,
        "deaths": safe_int(fields.get("muertos")),
        "injuries": safe_int(fields.get("heridos")),
        "missing_persons": safe_int(fields.get("desaparece")),
        "affected_population": safe_int(fields.get("afectados")),
        "evacuated_population": safe_int(fields.get("evacuados")),
        "houses_destroyed": safe_int(fields.get("vivdest")),
        "houses_damaged": safe_int(fields.get("vivafec")),
        "affected_families": safe_int(fields.get("damnificados")),
        "relocated_population": safe_int(fields.get("reubicados")),
        "hospitals_affected": safe_int(fields.get("nhospitales")),
        "schools_affected": safe_int(fields.get("nescuelas")),
        "agricultural_hectares": safe_float(fields.get("nhectareas")),
        "livestock_heads": safe_int(fields.get("cabezas")),
        "road_damage_km": safe_float(fields.get("kmvias")),
        "duration_days": safe_int(fields.get("duracion")),
        "economic_loss_local": safe_float(fields.get("valorloc")),
        "economic_loss_usd": safe_float(fields.get("valorus")),
        "location_description": fields.get("lugar", ""),
        "data_source_notes": fields.get("fuentes", ""),
        "latitude": safe_float(fields.get("latitude")),
        "longitude": safe_float(fields.get("longitude")),
        "sector_relief": safe_flag(fields.get("socorro")),
        "sector_health": safe_flag(fields.get("salud")),
        "sector_education": safe_flag(fields.get("educacion")),
        "sector_agriculture": safe_flag(fields.get("agropecuario")),
        "sector_industry": safe_flag(fields.get("industrias")),
        "sector_water": safe_flag(fields.get("acueducto")),
        "sector_sewer": safe_flag(fields.get("alcantarillado")),
        "sector_energy": safe_flag(fields.get("energia")),
        "sector_communications": safe_flag(fields.get("comunicaciones")),
        "sector_transport": safe_flag(fields.get("transporte")),
    }
