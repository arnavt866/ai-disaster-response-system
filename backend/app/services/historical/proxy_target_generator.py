"""Deterministic impact-based proxy resource-demand target generation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from app.config.settings import PROJECT_ROOT

DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT / "app" / "config" / "proxy_target_config.json"
)

TARGET_COLUMNS: tuple[str, ...] = (
    "food_packets_demand",
    "water_demand",
    "medical_kits_demand",
    "shelter_capacity_demand",
)


def load_proxy_target_config(
    config_path: Path | None = None,
) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _non_negative(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return 0.0


def compute_relief_population(row: dict[str, Any], config: dict[str, Any]) -> float:
    """
    Estimate relief population without double-counting affected and evacuated people.

    Evacuated people are typically a subset of affected people, so max() is used.
    """
    coefficients = config["coefficients"]
    affected = _non_negative(row.get("affected_population"))
    evacuated = _non_negative(row.get("evacuated_population"))
    families = _non_negative(row.get("affected_families"))

    relief_population = max(affected, evacuated)
    if relief_population == 0.0 and families > 0:
        relief_population = families * coefficients["assumed_persons_per_family"]

    return relief_population


def compute_proxy_targets_for_row(
    row: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute all four proxy targets for a single normalized historical record."""
    coefficients = config["coefficients"]
    relief_population = compute_relief_population(row, config)

    injuries = _non_negative(row.get("injuries"))
    deaths = _non_negative(row.get("deaths"))
    evacuated = _non_negative(row.get("evacuated_population"))
    houses_destroyed = _non_negative(row.get("houses_destroyed"))
    houses_damaged = _non_negative(row.get("houses_damaged"))
    families = _non_negative(row.get("affected_families"))

    food_packets = math.ceil(
        relief_population * coefficients["food_packets_per_person"]
    )
    water_demand = math.ceil(
        relief_population * coefficients["water_units_per_person"]
    )

    injury_component = injuries * coefficients["medical_kits_per_injury"]
    population_component = relief_population * coefficients["medical_population_rate"]
    severity_multiplier = (
        1.0 + deaths * coefficients["death_severity_indicator_weight"]
    )
    medical_kits = math.ceil(
        (injury_component + population_component) * severity_multiplier
    )

    shelter_from_evacuation = evacuated
    shelter_from_housing = (
        houses_destroyed * coefficients["shelter_per_destroyed_house"]
        + houses_damaged * coefficients["shelter_per_damaged_house"]
    )
    shelter_from_families = 0.0
    if relief_population == 0.0 and families > 0:
        shelter_from_families = (
            families * coefficients["assumed_persons_per_family"]
        )

    shelter_capacity = math.ceil(
        max(shelter_from_evacuation, shelter_from_housing, shelter_from_families)
    )

    return {
        "relief_population_proxy": relief_population,
        "food_packets_demand": int(food_packets),
        "water_demand": int(water_demand),
        "medical_kits_demand": int(medical_kits),
        "shelter_capacity_demand": int(shelter_capacity),
        "target_method": config["target_method"],
        "target_is_observed": config["target_is_observed"],
        "target_version": config["version"],
    }


def add_proxy_targets(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Add proxy target columns to a normalized historical DataFrame."""
    config = config or load_proxy_target_config()
    result = df.copy()

    target_rows = [
        compute_proxy_targets_for_row(row.to_dict(), config)
        for _, row in result.iterrows()
    ]
    target_df = pd.DataFrame(target_rows)
    return pd.concat([result.reset_index(drop=True), target_df], axis=1)


def validate_proxy_targets(df: pd.DataFrame) -> dict[str, Any]:
    """Run basic validity checks on generated proxy targets."""
    issues: list[str] = []

    for column in TARGET_COLUMNS:
        if column not in df.columns:
            issues.append(f"Missing target column: {column}")
            continue

        series = pd.to_numeric(df[column], errors="coerce")
        if series.isna().any():
            issues.append(f"{column} contains NaN values.")
        if (series < 0).any():
            issues.append(f"{column} contains negative values.")
        if numpy_is_inf(series):
            issues.append(f"{column} contains infinite values.")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def numpy_is_inf(series: pd.Series) -> bool:
    return bool(series.apply(lambda value: math.isinf(value) if pd.notna(value) else False).any())


def target_distribution_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Compute descriptive statistics for each proxy target."""
    summary: dict[str, Any] = {}

    for column in TARGET_COLUMNS:
        series = pd.to_numeric(df[column], errors="coerce")
        summary[column] = {
            "count": int(series.count()),
            "min": float(series.min()) if series.count() else None,
            "max": float(series.max()) if series.count() else None,
            "mean": float(series.mean()) if series.count() else None,
            "median": float(series.median()) if series.count() else None,
            "std": float(series.std()) if series.count() else None,
            "percentiles": {
                "p25": float(series.quantile(0.25)) if series.count() else None,
                "p50": float(series.quantile(0.50)) if series.count() else None,
                "p75": float(series.quantile(0.75)) if series.count() else None,
                "p90": float(series.quantile(0.90)) if series.count() else None,
                "p95": float(series.quantile(0.95)) if series.count() else None,
                "p99": float(series.quantile(0.99)) if series.count() else None,
            },
            "zero_count": int((series == 0).sum()),
            "zero_percentage": round(float((series == 0).mean() * 100), 2),
            "non_zero_count": int((series > 0).sum()),
            "non_zero_percentage": round(float((series > 0).mean() * 100), 2),
        }

    return summary


def target_correlation_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Correlate proxy targets with principal source variables (sanity check only)."""
    source_vars = [
        "relief_population_proxy",
        "affected_population",
        "evacuated_population",
        "affected_families",
        "injuries",
        "deaths",
        "houses_destroyed",
        "houses_damaged",
    ]
    available_sources = [col for col in source_vars if col in df.columns]
    columns = [*TARGET_COLUMNS, *available_sources]
    numeric_df = df[columns].apply(pd.to_numeric, errors="coerce")

    correlations: dict[str, dict[str, float | None]] = {}
    for target in TARGET_COLUMNS:
        correlations[target] = {}
        for source in available_sources:
            pair = numeric_df[[target, source]].dropna()
            if len(pair) < 2 or pair[source].std() == 0 or pair[target].std() == 0:
                correlations[target][source] = None
            else:
                correlations[target][source] = round(
                    float(pair[target].corr(pair[source])),
                    4,
                )

    return correlations
