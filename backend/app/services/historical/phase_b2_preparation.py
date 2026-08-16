"""Phase B2 pipeline: matching-report fix validation, proxy targets, ML dataset."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.config.settings import DATASET_DIR, REPORTS_DIR
from app.core.logger import logger
from app.services.historical.data_preparation import run_phase_b1
from app.services.historical.feature_schema import (
    ML_DATASET_COLUMNS,
    ML_FEATURE_COLUMNS,
    ML_PROVENANCE_COLUMNS,
    ML_TARGET_COLUMNS,
)
from app.services.historical.proxy_target_generator import (
    add_proxy_targets,
    load_proxy_target_config,
    target_correlation_summary,
    target_distribution_summary,
    validate_proxy_targets,
)


@dataclass
class PhaseB2Result:
    matching_summary: dict[str, Any]
    target_config: dict[str, Any]
    target_statistics: dict[str, Any]
    target_correlations: dict[str, Any]
    target_validation: dict[str, Any]
    dataset_shape: tuple[int, int]
    feature_columns: list[str]
    target_columns: list[str]
    data_quality_issues: list[str] = field(default_factory=list)
    output_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matching_summary": self.matching_summary,
            "target_config": self.target_config,
            "target_statistics": self.target_statistics,
            "target_correlations": self.target_correlations,
            "target_validation": self.target_validation,
            "dataset_shape": {
                "rows": self.dataset_shape[0],
                "columns": self.dataset_shape[1],
            },
            "feature_columns": self.feature_columns,
            "target_columns": self.target_columns,
            "data_quality_issues": self.data_quality_issues,
            "output_files": self.output_files,
        }


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)


def _build_feature_schema(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_method": config["target_method"],
        "target_is_observed": config["target_is_observed"],
        "target_version": config["version"],
        "methodology_description": config["methodology_description"],
        "feature_columns": list(ML_FEATURE_COLUMNS),
        "target_columns": list(ML_TARGET_COLUMNS),
        "provenance_columns": list(ML_PROVENANCE_COLUMNS),
        "dataset_columns": list(ML_DATASET_COLUMNS),
        "coefficients": config["coefficients"],
        "units": config["units"],
        "formulas": config["formulas"],
        "source_variables": config["source_variables"],
        "assumptions": config["assumptions"],
    }


def _check_correlation_sanity(correlations: dict[str, Any]) -> list[str]:
    """Flag unexpected correlation signs for manual review."""
    issues: list[str] = []

    food = correlations.get("food_packets_demand", {})
    water = correlations.get("water_demand", {})
    medical = correlations.get("medical_kits_demand", {})
    shelter = correlations.get("shelter_capacity_demand", {})

    expected_positive = [
        (food, "relief_population_proxy", "food vs relief_population"),
        (water, "relief_population_proxy", "water vs relief_population"),
        (medical, "injuries", "medical vs injuries"),
        (shelter, "houses_destroyed", "shelter vs houses_destroyed"),
        (shelter, "evacuated_population", "shelter vs evacuated_population"),
    ]

    for mapping, key, label in expected_positive:
        value = mapping.get(key)
        if value is not None and value < 0:
            issues.append(f"Unexpected negative correlation: {label} ({value})")

    return issues


def run_phase_b2(
    normalized_csv: Path | None = None,
    config_path: Path | None = None,
) -> PhaseB2Result:
    """
    Run Phase B2:
    1. Re-run B1 to refresh matching report with reconciled counts.
    2. Generate proxy targets.
    3. Build historical_ml_dataset.csv and reports.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Phase B2: refreshing B1 outputs for reconciled matching report")
    b1_result = run_phase_b1()
    matching_summary = b1_result.matching_report.get("district_summary", {})

    normalized_path = normalized_csv or Path(
        b1_result.output_files["normalized_csv"]
    )
    df = pd.read_csv(normalized_path)
    logger.info("Phase B2: loaded %d normalized records", len(df))

    config = load_proxy_target_config(config_path)
    logger.info("Phase B2: generating proxy targets (%s)", config["target_method"])
    df_with_targets = add_proxy_targets(df, config)

    target_validation = validate_proxy_targets(df_with_targets)
    target_statistics = target_distribution_summary(df_with_targets)
    target_correlations = target_correlation_summary(df_with_targets)

    ml_dataset = df_with_targets[
        [col for col in ML_DATASET_COLUMNS if col in df_with_targets.columns]
    ].copy()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ml_csv = DATASET_DIR / "historical_ml_dataset.csv"
    schema_json = DATASET_DIR / "historical_ml_feature_schema.json"
    target_stats_json = REPORTS_DIR / f"proxy_target_statistics_{timestamp}.json"
    target_corr_json = REPORTS_DIR / f"proxy_target_correlations_{timestamp}.json"
    summary_json = REPORTS_DIR / f"phase_b2_summary_{timestamp}.json"
    target_md = REPORTS_DIR / f"proxy_target_methodology_{timestamp}.md"

    ml_dataset.to_csv(ml_csv, index=False)
    feature_schema = _build_feature_schema(config)
    _write_json(schema_json, feature_schema)
    _write_json(target_stats_json, target_statistics)
    _write_json(target_corr_json, target_correlations)

    quality_issues = list(b1_result.data_quality_issues)
    quality_issues.extend(target_validation.get("issues", []))
    quality_issues.extend(_check_correlation_sanity(target_correlations))

    methodology_lines = [
        "# Proxy Target Methodology (Phase B2)",
        "",
        f"Generated: {timestamp}",
        "",
        f"**{config['methodology_description']}**",
        "",
        "## Configuration",
        f"- Method: `{config['target_method']}`",
        f"- Version: `{config['version']}`",
        f"- Observed labels: `{config['target_is_observed']}`",
        "",
        "## Formulas",
    ]
    for name, formula in config["formulas"].items():
        methodology_lines.append(f"- **{name}**: `{formula}`")

    methodology_lines.extend(["", "## Coefficients"])
    for name, value in config["coefficients"].items():
        methodology_lines.append(f"- `{name}` = {value}")

    methodology_lines.extend(["", "## Units"])
    for name, unit in config["units"].items():
        methodology_lines.append(f"- `{name}`: {unit}")

    target_md.write_text("\n".join(methodology_lines), encoding="utf-8")

    result = PhaseB2Result(
        matching_summary=matching_summary,
        target_config=config,
        target_statistics=target_statistics,
        target_correlations=target_correlations,
        target_validation=target_validation,
        dataset_shape=(len(ml_dataset), len(ml_dataset.columns)),
        feature_columns=list(ML_FEATURE_COLUMNS),
        target_columns=list(ML_TARGET_COLUMNS),
        data_quality_issues=quality_issues,
        output_files={
            "historical_ml_dataset_csv": str(ml_csv),
            "feature_schema_json": str(schema_json),
            "proxy_target_statistics_json": str(target_stats_json),
            "proxy_target_correlations_json": str(target_corr_json),
            "proxy_target_methodology_md": str(target_md),
            "phase_b2_summary_json": str(summary_json),
            "normalized_csv": str(normalized_path),
            "district_matching_report_json": b1_result.output_files.get(
                "matching_report_json", ""
            ),
        },
    )

    _write_json(summary_json, result.to_dict())
    logger.info("Phase B2 complete. ML dataset written to %s", ml_csv)
    return result
