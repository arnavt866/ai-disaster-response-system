#!/usr/bin/env python3
"""Validate scenario-pack historical figures against prediction/allocation pipeline.

Reads cited CSVs under data/scenarios/, creates ephemeral Active DisasterZone rows
(matching real taluk/district coordinates where available), runs
predict_demand_for_zone and optimize_allocation(persist=False), and compares model
demand to deterministic proxy targets derived from the same CSV historical fields.

Does not retrain models or persist zones/allocation records (session rolled back).
"""

from __future__ import annotations

import math
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import MODEL_DIR, PROJECT_ROOT
from app.database.connection import SessionLocal
from app.models.disaster_zone import DisasterZone
from app.services.historical.feature_schema import ML_TARGET_COLUMNS
from app.services.historical.proxy_target_generator import (
    compute_proxy_targets_for_row,
    load_proxy_target_config,
)
from app.services.optimization.allocation_service import optimize_allocation
from app.services.optimization.constants import DEMAND_TO_INVENTORY_CATEGORY
from app.services.prediction.inference import ModelArtifactsNotFoundError
from app.services.prediction.zone_integration_service import predict_demand_for_zone

SCENARIOS_ROOT = PROJECT_ROOT / "data" / "scenarios"
CHENNAI_CSV = SCENARIOS_ROOT / "chennai_floods_2015" / "district_metrics.csv"
CHENNAI_KML = SCENARIOS_ROOT / "chennai_floods_2015" / "gis" / "tiruvallur_flood_hotspots.kml"
KERALA_CSV = SCENARIOS_ROOT / "kerala_floods_2018" / "district_metrics.csv"

TARGET_LABELS = {
    "food_packets_demand": "food",
    "water_demand": "water",
    "medical_kits_demand": "medical",
    "shelter_capacity_demand": "shelter",
}

# Approximate district HQ coordinates (WGS84) for Kerala PDNA Table 3 districts.
KERALA_DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Kollam": (8.8932, 76.6141),
    "Pathanamthitta": (9.2648, 76.7870),
    "Alappuzha": (9.4981, 76.3388),
    "Kottayam": (9.5916, 76.5222),
    "Idukki": (9.9189, 76.9449),
    "Ernakulam": (9.9816, 76.2999),
    "Thrissur": (10.5276, 76.2144),
    "Palakkad": (10.7867, 76.6548),
    "Malappuram": (11.0510, 76.0711),
    "Kozhikode": (11.2588, 75.7804),
    "Wayanad": (11.6854, 76.1320),
    "Kannur": (11.8745, 75.3704),
    "Kasaragod": (12.4996, 74.9869),
}

CHENNAI_FALLBACK_CENTROID = (13.1149, 80.1415)  # Tiruvallur hotspots KML aggregate
KERALA_STATE_CENTROID = (10.8505, 76.2711)


@dataclass
class ZoneSpec:
    scenario: str
    label: str
    latitude: float
    longitude: float
    disaster_type: str
    severity: str
    event_year: int
    event_month: int
    state: str
    district: str
    historical: dict[str, Any] = field(default_factory=dict)
    csv_notes: str = ""


@dataclass
class ComparisonRow:
    scenario: str
    label: str
    target: str
    historical_proxy: int
    model_predicted: int
    allocation_demanded: float
    allocation_allocated: float
    ratio_model_to_proxy: float | None
    notes: str = ""


def _safe_int(value: Any) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _pct_delta(model: int, proxy: int) -> str:
    if proxy == 0:
        if model == 0:
            return "both zero"
        return "proxy zero, model non-zero (undefined ratio)"
    ratio = model / proxy
    return f"{ratio:.2f}x ({model - proxy:+d})"


def load_chennai_taluk_centroids() -> dict[str, tuple[float, float]]:
    if not CHENNAI_KML.exists():
        return {}
    gdf = gpd.read_file(CHENNAI_KML)
    if "name_region" not in gdf.columns:
        return {}
    grouped = (
        gdf.dropna(subset=["latitude", "longitude"])
        .groupby("name_region")[["latitude", "longitude"]]
        .mean()
    )
    return {
        str(name): (float(row.latitude), float(row.longitude))
        for name, row in grouped.iterrows()
    }


def _resolve_chennai_centroid(taluk: str, centroids: dict[str, tuple[float, float]]) -> tuple[float, float, str]:
    if taluk in centroids:
        lat, lon = centroids[taluk]
        return lat, lon, f"KML centroid ({taluk})"
    aliases = {
        "Poonamallee": "Poonamalli",
    }
    alias = aliases.get(taluk)
    if alias and alias in centroids:
        lat, lon = centroids[alias]
        return lat, lon, f"KML centroid via alias {alias}"
    lat, lon = CHENNAI_FALLBACK_CENTROID
    return lat, lon, "fallback Tiruvallur aggregate (no KML match)"


def chennai_zone_specs() -> list[ZoneSpec]:
    df = pd.read_csv(CHENNAI_CSV)
    centroids = load_chennai_taluk_centroids()
    specs: list[ZoneSpec] = []
    for _, row in df.iterrows():
        taluk = str(row["taluk"])
        lat, lon, loc_note = _resolve_chennai_centroid(taluk, centroids)
        affected = _safe_int(row.get("affected_population"))
        destroyed = _safe_int(row.get("houses_destroyed"))
        damaged = _safe_int(row.get("houses_damaged"))
        specs.append(
            ZoneSpec(
                scenario="Chennai Floods 2015",
                label=taluk,
                latitude=lat,
                longitude=lon,
                disaster_type="Flood",
                severity=str(row.get("severity_level") or "Moderate"),
                event_year=2015,
                event_month=12,
                state="Tamil Nadu",
                district=taluk,
                historical={
                    "affected_population": affected,
                    "evacuated_population": 0,
                    "deaths": 0,
                    "injuries": 0,
                    "houses_destroyed": destroyed,
                    "houses_damaged": damaged,
                },
                csv_notes=(
                    f"{loc_note}; CSV affected_population={affected}, "
                    f"houses_damaged={damaged}, houses_destroyed={destroyed}"
                ),
            )
        )
    return specs


def kerala_zone_specs() -> list[ZoneSpec]:
    df = pd.read_csv(KERALA_CSV)
    specs: list[ZoneSpec] = []

    human = df[df["row_type"] == "statewide_summary"].iloc[0]
    housing = df[df["row_type"] == "statewide_summary"].iloc[1]
    specs.append(
        ZoneSpec(
            scenario="Kerala Floods 2018",
            label="Kerala (statewide)",
            latitude=KERALA_STATE_CENTROID[0],
            longitude=KERALA_STATE_CENTROID[1],
            disaster_type="Flood",
            severity="Critical",
            event_year=2018,
            event_month=8,
            state="Kerala",
            district="Kerala",
            historical={
                "affected_population": _safe_int(human.get("affected_population")),
                "evacuated_population": _safe_int(human.get("displaced_population")),
                "deaths": _safe_int(human.get("deaths")),
                "injuries": 0,
                "houses_destroyed": _safe_int(housing.get("buildings_to_rebuild")),
                "houses_damaged": max(
                    0,
                    _safe_int(housing.get("total_buildings_affected"))
                    - _safe_int(housing.get("buildings_to_rebuild")),
                ),
            },
            csv_notes=(
                "PDNA Executive Summary p.10 (5.4M affected, 1.4M displaced, 433 deaths); "
                "housing Table 3 totals pp.91-92"
            ),
        )
    )

    districts = df[df["row_type"] == "district_housing"]
    for _, row in districts.iterrows():
        district = str(row["geography"])
        lat, lon = KERALA_DISTRICT_COORDS.get(district, KERALA_STATE_CENTROID)
        rebuild = _safe_int(row.get("buildings_to_rebuild"))
        total_houses = _safe_int(row.get("total_buildings_affected"))
        specs.append(
            ZoneSpec(
                scenario="Kerala Floods 2018",
                label=district,
                latitude=lat,
                longitude=lon,
                disaster_type="Flood",
                severity="High" if total_houses >= 10_000 else "Moderate",
                event_year=2018,
                event_month=8,
                state="Kerala",
                district=district,
                historical={
                    "affected_population": 0,
                    "evacuated_population": 0,
                    "deaths": 0,
                    "injuries": 0,
                    "houses_destroyed": rebuild,
                    "houses_damaged": max(0, total_houses - rebuild),
                },
                csv_notes=(
                    "PDNA Table 3 district housing only; no district affected_population in PDNA"
                ),
            )
        )
    return specs


def _historical_field_report_overrides(historical: dict[str, Any]) -> dict[str, Any] | None:
    """Map scenario CSV historical impact fields into ML feature overrides.

    Live zone prediction defaults evacuation/housing features to zero until field
    reports arrive. Scenario validation supplies known historical values so the
    model receives the same drivers used at training label time.
    """
    overrides: dict[str, Any] = {}
    for key in (
        "evacuated_population",
        "houses_destroyed",
        "houses_damaged",
        "injuries",
        "deaths",
        "affected_families",
    ):
        if key not in historical:
            continue
        value = _safe_int(historical.get(key))
        if value > 0:
            overrides[key] = value
    return overrides or None


def _historical_proxy_row(spec: ZoneSpec, config: dict[str, Any]) -> dict[str, Any]:
    row = {
        "disaster_type_normalized": spec.disaster_type,
        "event_year": spec.event_year,
        "event_month": spec.event_month,
        "state_normalized": spec.state,
        "district_normalized": spec.district,
        **spec.historical,
    }
    return compute_proxy_targets_for_row(row, config)


def create_ephemeral_zone(db: Session, spec: ZoneSpec) -> DisasterZone:
    zone = DisasterZone(
        zone_name=f"VALIDATION-{spec.scenario}-{spec.label}",
        disaster_type=spec.disaster_type,
        severity=spec.severity,
        latitude=spec.latitude,
        longitude=spec.longitude,
        affected_population=_safe_int(spec.historical.get("affected_population")),
        status="Active",
        operational_priority=spec.severity if spec.severity in {"Critical", "High", "Moderate", "Low"} else "Moderate",
    )
    db.add(zone)
    db.flush()
    return zone


def validate_zone(
    db: Session,
    spec: ZoneSpec,
    *,
    proxy_config: dict[str, Any],
) -> tuple[list[ComparisonRow], dict[str, Any]]:
    zone = create_ephemeral_zone(db, spec)
    proxy = _historical_proxy_row(spec, proxy_config)
    field_overrides = _historical_field_report_overrides(spec.historical)

    prediction = predict_demand_for_zone(
        db,
        zone.id,
        update_source="scenario_validation",
        field_report_overrides=field_overrides,
    )
    model_preds = prediction["demand"]["prediction"]["predictions"]

    allocation = optimize_allocation(
        db,
        [zone.id],
        persist=False,
        reserve_inventory=False,
    )

    alloc_by_target: dict[str, dict[str, float]] = {t: {"demanded": 0.0, "allocated": 0.0} for t in ML_TARGET_COLUMNS}
    for row in allocation.get("allocations", []):
        category = row.get("resource_category")
        for target, inv_cat in DEMAND_TO_INVENTORY_CATEGORY.items():
            if inv_cat == category:
                alloc_by_target[target]["demanded"] = float(row.get("demanded", 0))
                alloc_by_target[target]["allocated"] = float(row.get("allocated", 0))

    grid_pop = prediction.get("milestone1_grid_analysis", {}).get("estimated_population")
    notes = spec.csv_notes
    if grid_pop is not None and grid_pop != zone.affected_population:
        notes += f"; grid_analysis_population={grid_pop}"

    rows: list[ComparisonRow] = []
    for target in ML_TARGET_COLUMNS:
        proxy_val = int(proxy.get(target, 0))
        model_val = int(round(model_preds[target]["point_estimate"]))
        ratio = (model_val / proxy_val) if proxy_val > 0 else None
        rows.append(
            ComparisonRow(
                scenario=spec.scenario,
                label=spec.label,
                target=TARGET_LABELS[target],
                historical_proxy=proxy_val,
                model_predicted=model_val,
                allocation_demanded=alloc_by_target[target]["demanded"],
                allocation_allocated=alloc_by_target[target]["allocated"],
                ratio_model_to_proxy=ratio,
                notes=notes if target == ML_TARGET_COLUMNS[0] else "",
            )
        )
    return rows, {
        "zone_id": zone.id,
        "allocation_status": allocation.get("status"),
        "relief_population_proxy": proxy.get("relief_population_proxy"),
    }


def print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def print_comparison_table(rows: list[ComparisonRow]) -> None:
    if not rows:
        print("(no rows)")
        return
    current_label = None
    for row in rows:
        if row.label != current_label:
            current_label = row.label
            print(f"\n--- {row.label} ({row.scenario}) ---")
            if row.notes:
                print(f"  source: {row.notes}")
        ratio_text = (
            f"{row.ratio_model_to_proxy:.2f}x"
            if row.ratio_model_to_proxy is not None
            else _pct_delta(row.model_predicted, row.historical_proxy)
        )
        print(
            f"  {row.target:7s}  proxy={row.historical_proxy:>10,d}  "
            f"model={row.model_predicted:>10,d}  ({ratio_text})  "
            f"alloc_demanded={row.allocation_demanded:>10,.0f}  "
            f"alloc_allocated={row.allocation_allocated:>10,.0f}"
        )


def summarize_scenario(rows: list[ComparisonRow], scenario: str) -> None:
    subset = [r for r in rows if r.scenario == scenario]
    if not subset:
        return
    print_section(f"Summary — {scenario}")
    for target in sorted({r.target for r in subset}):
        proxy_sum = sum(r.historical_proxy for r in subset if r.target == target)
        model_sum = sum(r.model_predicted for r in subset if r.target == target)
        print(
            f"  {target:7s}  total_proxy={proxy_sum:>12,d}  total_model={model_sum:>12,d}  "
            f"({_pct_delta(model_sum, proxy_sum)})"
        )


def main() -> int:
    logging.getLogger("app.services.optimization.allocation_service").setLevel(logging.ERROR)

    if not (MODEL_DIR / "model_registry.json").exists():
        print(f"ERROR: trained model artifacts missing under {MODEL_DIR}")
        return 1

    proxy_config = load_proxy_target_config()
    all_specs = chennai_zone_specs() + kerala_zone_specs()
    all_rows: list[ComparisonRow] = []

    print_section("Scenario pack validation (ephemeral zones, rollback after run)")
    print(f"Chennai CSV: {CHENNAI_CSV}")
    print(f"Kerala CSV:  {KERALA_CSV}")
    print(f"Zones to validate: {len(all_specs)}")

    db = SessionLocal()
    try:
        for spec in all_specs:
            try:
                rows, _meta = validate_zone(db, spec, proxy_config=proxy_config)
                all_rows.extend(rows)
            except ModelArtifactsNotFoundError as exc:
                print(f"ERROR: {exc}")
                return 1
            except Exception as exc:
                print(f"FAILED {spec.scenario} / {spec.label}: {exc}")
                raise
        db.rollback()
    finally:
        db.close()

    print_section("Chennai Floods 2015 — per taluk")
    print(
        "NOTE: CSV affected_population and housing counts are all zero (KML hotspot names only). "
        "Proxy demand from CSV is therefore zero; any non-zero model output comes from grid/building "
        "context, not cited population figures."
    )
    print_comparison_table([r for r in all_rows if r.scenario == "Chennai Floods 2015"])

    print_section("Kerala Floods 2018 — statewide + districts")
    print(
        "NOTE: PDNA publishes statewide affected population (5.4M) but not district breakdown. "
        "District rows use Table 3 housing counts only; proxy food/water will be zero at district level. "
        "Shelter model receives historical evacuation/housing via field_report_overrides."
    )
    print_comparison_table([r for r in all_rows if r.scenario == "Kerala Floods 2018"])

    summarize_scenario(all_rows, "Chennai Floods 2015")
    summarize_scenario(all_rows, "Kerala Floods 2018")

    # Plain assessment
    print_section("Assessment")
    kerala_state = next(
        (r for r in all_rows if r.label == "Kerala (statewide)" and r.target == "food"),
        None,
    )
    if kerala_state:
        print(
            f"  Kerala statewide food: CSV-proxy={kerala_state.historical_proxy:,} vs "
            f"model={kerala_state.model_predicted:,} ({_pct_delta(kerala_state.model_predicted, kerala_state.historical_proxy)})"
        )
        if kerala_state.historical_proxy > 0:
            ratio = kerala_state.model_predicted / kerala_state.historical_proxy
            if ratio < 0.25 or ratio > 4.0:
                print(
                    "  WARNING: statewide food prediction differs from population-proxy by more than 4x — "
                    "model scale does not align with simple affected-population proxy."
                )

    chennai_nonzero_model = [
        r
        for r in all_rows
        if r.scenario == "Chennai Floods 2015" and r.historical_proxy == 0 and r.model_predicted > 0
    ]
    if chennai_nonzero_model:
        print(
            f"  Chennai: {len(chennai_nonzero_model)} taluk×resource cells have model>0 while CSV-proxy=0 "
            "(expected — CSV lacks population/housing numbers)."
        )

    kerala_shelter_districts = [
        r
        for r in all_rows
        if r.scenario == "Kerala Floods 2018"
        and r.label != "Kerala (statewide)"
        and r.target == "shelter"
        and r.historical_proxy > 0
    ]
    wild = [
        r
        for r in kerala_shelter_districts
        if r.historical_proxy > 0
        and (r.model_predicted / r.historical_proxy < 0.1 or r.model_predicted / r.historical_proxy > 10)
    ]
    if wild:
        print(
            f"  WARNING: {len(wild)} Kerala district shelter predictions diverge >10x from housing-proxy "
            "(model trained on historical impact mix, not PDNA housing table alone)."
        )

    print("\nValidation complete (no scenario zones persisted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
