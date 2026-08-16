"""Phase B1 data-preparation pipeline: validation, parsing, normalization, reports."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.config.settings import (
    DATASET_DIR,
    HISTORICAL_XML_PATHS,
    REPORTS_DIR,
    TARGET_DISTRICTS_GEOJSON,
)
from app.core.logger import logger
from app.services.historical.desinventar_parser import (
    parse_all_historical_xml,
)
from app.services.historical.district_matcher import match_records_to_districts
from app.services.historical.district_validator import validate_target_districts_geojson
from app.services.historical.historical_normalizer import (
    NORMALIZED_FEATURE_COLUMNS,
    normalize_record,
)


@dataclass
class PhaseB1Result:
    geo_validation: dict[str, Any]
    xml_inspections: list[dict[str, Any]]
    parsed_record_counts: dict[str, int]
    dataset_shape: tuple[int, int]
    matched_district_count: int
    matching_report: dict[str, Any]
    missing_value_summary: dict[str, Any]
    feature_summary: dict[str, Any]
    data_quality_issues: list[str] = field(default_factory=list)
    output_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "geo_validation": self.geo_validation,
            "xml_inspections": self.xml_inspections,
            "parsed_record_counts": self.parsed_record_counts,
            "dataset_shape": {
                "rows": self.dataset_shape[0],
                "columns": self.dataset_shape[1],
            },
            "matched_district_count": self.matched_district_count,
            "matching_report": self.matching_report,
            "missing_value_summary": self.missing_value_summary,
            "feature_summary": self.feature_summary,
            "data_quality_issues": self.data_quality_issues,
            "output_files": self.output_files,
        }


def _ensure_output_dirs() -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR, DATASET_DIR


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)


def _missing_value_summary(df: pd.DataFrame) -> dict[str, Any]:
    total = len(df)
    missing_counts = df.isna().sum().to_dict()
    missing_pct = {
        col: round((count / total) * 100, 2) if total else 0.0
        for col, count in missing_counts.items()
    }
    return {
        "total_records": total,
        "missing_counts": missing_counts,
        "missing_percentages": missing_pct,
    }


def _feature_summary(df: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "available_features": list(NORMALIZED_FEATURE_COLUMNS),
        "disaster_type_counts": dict(
            Counter(df["disaster_type_normalized"].dropna())
        ),
        "records_by_state": dict(Counter(df["source_state"])),
        "records_by_year": dict(
            Counter(
                int(y) for y in df["event_year"].dropna() if pd.notna(y)
            )
        ),
        "numeric_feature_stats": {},
    }

    numeric_cols = [
        "deaths",
        "injuries",
        "affected_population",
        "evacuated_population",
        "houses_destroyed",
        "houses_damaged",
        "hospitals_affected",
        "schools_affected",
    ]
    for col in numeric_cols:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce")
            summary["numeric_feature_stats"][col] = {
                "non_null": int(series.notna().sum()),
                "zero_values": int((series == 0).sum()),
                "positive_values": int((series > 0).sum()),
                "max": float(series.max()) if series.notna().any() else None,
            }

    return summary


def _detect_data_quality_issues(
    df: pd.DataFrame,
    matching_report: dict[str, Any],
    geo_validation: dict[str, Any],
) -> list[str]:
    issues: list[str] = []

    if not geo_validation.get("valid"):
        issues.append(
            "Target districts GeoJSON failed validation: "
            + "; ".join(geo_validation.get("errors", []))
        )

    if matching_report.get("unmatched_historical_districts"):
        issues.append(
            f"{len(matching_report['unmatched_historical_districts'])} "
            "historical district names could not be matched to GeoJSON."
        )

    if matching_report.get("unmatched_geojson_districts"):
        issues.append(
            f"{len(matching_report['unmatched_geojson_districts'])} "
            "GeoJSON districts have no matching historical XML records."
        )

    null_dates = int(df["event_date"].isna().sum())
    if null_dates:
        issues.append(
            f"{null_dates} records ({round(null_dates/len(df)*100,1)}%) "
            "have unparseable or missing event dates."
        )

    # Confirm no resource-demand label columns exist.
    forbidden = {"food_packets", "water_bottles", "medical_kits", "shelter_capacity"}
    present = forbidden.intersection(df.columns)
    if present:
        issues.append(
            f"Unexpected resource-demand columns present (should not exist in B1): {present}"
        )

    return issues


def run_phase_b1(
    target_geojson: Path | None = None,
    xml_paths: dict[str, Path] | None = None,
    output_dir: Path | None = None,
) -> PhaseB1Result:
    """
    Execute the Phase B1 pipeline end-to-end.

    Raises ValueError if the target GeoJSON validation fails.
    """
    reports_dir, dataset_dir = _ensure_output_dirs()
    if output_dir:
        reports_dir = output_dir
        reports_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_geojson or TARGET_DISTRICTS_GEOJSON
    xml_map = xml_paths or HISTORICAL_XML_PATHS

    logger.info("Phase B1: validating target districts GeoJSON at %s", target_path)
    geo_validation = validate_target_districts_geojson(target_path)
    geo_dict = geo_validation.to_dict()

    if not geo_validation.valid:
        raise ValueError(
            "Target districts GeoJSON validation failed: "
            + "; ".join(geo_validation.errors)
        )

    logger.info("Phase B1: parsing historical XML datasets")
    raw_records, inspections = parse_all_historical_xml(xml_map)

    parsed_counts = Counter()
    for record in raw_records:
        parsed_counts[record.source_state] += 1

    logger.info("Phase B1: normalizing %d records", len(raw_records))
    normalized = [normalize_record(r) for r in raw_records]

    logger.info("Phase B1: matching districts")
    matched_records, matching_report = match_records_to_districts(
        normalized,
        geo_validation,
    )

    df = pd.DataFrame(matched_records)

    # Ensure consistent column ordering; append match metadata columns.
    extra_cols = [c for c in df.columns if c not in NORMALIZED_FEATURE_COLUMNS]
    ordered_cols = list(NORMALIZED_FEATURE_COLUMNS) + sorted(extra_cols)
    df = df[[c for c in ordered_cols if c in df.columns]]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Write outputs.
    normalized_csv = dataset_dir / "historical_normalized.csv"
    normalized_parquet = dataset_dir / "historical_normalized.parquet"
    df.to_csv(normalized_csv, index=False)
    try:
        df.to_parquet(normalized_parquet, index=False)
    except Exception as exc:
        logger.warning("Could not write parquet file: %s", exc)
        normalized_parquet = None

    matching_json = reports_dir / f"district_matching_report_{timestamp}.json"
    matching_md = reports_dir / f"district_matching_report_{timestamp}.md"
    stats_json = reports_dir / f"historical_dataset_stats_{timestamp}.json"
    schema_json = reports_dir / f"xml_schema_inspection_{timestamp}.json"
    summary_json = reports_dir / f"phase_b1_summary_{timestamp}.json"

    matching_dict = matching_report.to_dict()
    district_summary = matching_dict.get("district_summary", {})
    _write_json(matching_json, matching_dict)
    _write_json(schema_json, [i.to_dict() for i in inspections])

    missing_summary = _missing_value_summary(df)
    feature_summary = _feature_summary(df)
    quality_issues = _detect_data_quality_issues(df, matching_dict, geo_dict)

    stats_payload = {
        "generated_at": timestamp,
        "parsed_record_counts": dict(parsed_counts),
        "dataset_shape": {"rows": len(df), "columns": len(df.columns)},
        "district_summary": district_summary,
        "missing_value_summary": missing_summary,
        "feature_summary": feature_summary,
        "data_quality_issues": quality_issues,
    }
    _write_json(stats_json, stats_payload)

    # Human-readable matching report.
    md_lines = [
        "# District Matching Report (Phase B1)",
        "",
        f"Generated: {timestamp}",
        "",
        "## Reconciled District Counts",
        f"- Total GeoJSON districts: "
        f"{district_summary.get('total_geojson_districts', 'N/A')}",
        f"- Unique GeoJSON districts with historical data: "
        f"{district_summary.get('unique_geojson_districts_with_historical_data', 'N/A')}",
        f"- Unique GeoJSON districts without historical data: "
        f"{district_summary.get('unique_geojson_districts_without_historical_data', 'N/A')}",
        f"- Unique historical XML district names: "
        f"{district_summary.get('unique_historical_xml_district_names', 'N/A')}",
        f"- XML→GeoJSON mapping pairs: "
        f"{district_summary.get('xml_to_geo_mapping_pair_count', 'N/A')}",
        f"- Matched records: {district_summary.get('matched_records', 'N/A')}",
        f"- Unmatched records: {district_summary.get('unmatched_records', 'N/A')}",
        f"- Reconciliation: {district_summary.get('reconciliation_check', 'N/A')}",
        "",
        district_summary.get("counting_note", ""),
        "",
        "## Many-to-One Mappings",
    ]
    for entry in matching_dict.get("many_to_one_mappings", []):
        md_lines.append(
            f"- {entry['state']} / `{entry['geojson_district']}` ← "
            f"{', '.join(f'`{name}`' for name in entry['xml_districts'])}"
        )

    md_lines.extend(["", "## Alias Mappings Used"])
    for entry in matching_dict["alias_mappings_used"]:
        md_lines.append(
            f"- {entry['state']}: `{entry['xml_district_key']}` → "
            f"`{entry['geojson_district']}`"
        )

    md_lines.extend(["", "## Unmatched Historical Districts"])
    for entry in matching_dict["unmatched_historical_districts"]:
        md_lines.append(
            f"- {entry['state']} / `{entry['district_raw_key']}` "
            f"({entry['record_count']} records)"
        )

    md_lines.extend(["", "## Unmatched GeoJSON Districts"])
    for entry in matching_dict["unmatched_geojson_districts"]:
        md_lines.append(
            f"- {entry['state']} / `{entry['geojson_district']}`"
        )

    matching_md.write_text("\n".join(md_lines), encoding="utf-8")

    result = PhaseB1Result(
        geo_validation=geo_dict,
        xml_inspections=[i.to_dict() for i in inspections],
        parsed_record_counts=dict(parsed_counts),
        dataset_shape=(len(df), len(df.columns)),
        matched_district_count=district_summary.get(
            "unique_geojson_districts_with_historical_data", 0
        ),
        matching_report=matching_dict,
        missing_value_summary=missing_summary,
        feature_summary=feature_summary,
        data_quality_issues=quality_issues,
        output_files={
            "normalized_csv": str(normalized_csv),
            **({"normalized_parquet": str(normalized_parquet)} if normalized_parquet else {}),
            "matching_report_json": str(matching_json),
            "matching_report_md": str(matching_md),
            "dataset_stats_json": str(stats_json),
            "xml_schema_json": str(schema_json),
            "phase_b1_summary_json": str(summary_json),
        },
    )

    _write_json(summary_json, result.to_dict())
    logger.info("Phase B1 complete. Summary written to %s", summary_json)
    return result
