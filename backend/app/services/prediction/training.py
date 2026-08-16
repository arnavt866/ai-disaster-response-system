"""Model training, comparison, and artifact persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from app.config.settings import DATASET_DIR, MODEL_DIR, REPORTS_DIR
from app.core.logger import logger
from app.services.historical.feature_schema import (
    ML_FEATURE_COLUMNS,
    ML_PROVENANCE_COLUMNS,
    ML_TARGET_COLUMNS,
)
from app.services.prediction.evaluation import overfitting_flag, regression_metrics
from app.services.prediction.preprocessing import build_preprocessor
from app.services.prediction.uncertainty import ConformalIntervalEstimator

RANDOM_SEED = 42
MODEL_CANDIDATES = ("ridge", "random_forest", "xgboost")
SELECTION_CRITERION = "lowest_validation_rmse"


@dataclass
class SplitMetadata:
    strategy: str
    train_years: list[int]
    validation_years: list[int]
    test_years: list[int]
    train_size: int
    validation_size: int
    test_size: int
    calibration_size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "train_years": self.train_years,
            "validation_years": self.validation_years,
            "test_years": self.test_years,
            "train_size": self.train_size,
            "validation_size": self.validation_size,
            "test_size": self.test_size,
            "calibration_size": self.calibration_size,
        }


def _estimator_for_model(model_name: str):
    if model_name == "ridge":
        return Ridge(alpha=1.0, random_state=RANDOM_SEED)
    if model_name == "random_forest":
        return RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=5,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
    if model_name == "xgboost":
        return XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=RANDOM_SEED,
            objective="reg:squarederror",
            n_jobs=-1,
        )
    raise ValueError(f"Unknown model: {model_name}")


def build_model_pipeline(model_name: str) -> Pipeline:
    scale_numeric = model_name == "ridge"
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(scale_numeric=scale_numeric)),
            ("model", _estimator_for_model(model_name)),
        ]
    )


def time_aware_split(
    df: pd.DataFrame,
    year_col: str = "event_year",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, SplitMetadata]:
    """Chronological split by event year (no random shuffling)."""
    years = sorted(int(y) for y in df[year_col].dropna().unique())
    n_years = len(years)
    train_end = max(1, int(n_years * train_ratio))
    val_end = max(train_end + 1, int(n_years * (train_ratio + val_ratio)))

    train_years = years[:train_end]
    val_years = years[train_end:val_end]
    test_years = years[val_end:] or [years[-1]]

    train_df = df[df[year_col].isin(train_years)].copy()
    val_df = df[df[year_col].isin(val_years)].copy()
    test_df = df[df[year_col].isin(test_years)].copy()

    if test_df.empty:
        test_df = val_df.copy()
        val_df = train_df.sample(frac=0.15, random_state=RANDOM_SEED)

    # Calibration split from training tail (latest 15% of train years).
    cal_years = train_years[-max(1, len(train_years) // 5) :]
    cal_df = train_df[train_df[year_col].isin(cal_years)].copy()
    fit_train_df = train_df[~train_df[year_col].isin(cal_years)].copy()
    if fit_train_df.empty:
        fit_train_df = train_df.copy()
        cal_df = val_df.copy()

    metadata = SplitMetadata(
        strategy="chronological_by_event_year",
        train_years=train_years,
        validation_years=val_years,
        test_years=test_years,
        train_size=len(fit_train_df),
        validation_size=len(val_df),
        test_size=len(test_df),
        calibration_size=len(cal_df),
    )
    return fit_train_df, val_df, test_df, cal_df, metadata


def _prepare_xy(
    df: pd.DataFrame,
    target: str,
) -> tuple[pd.DataFrame, pd.Series]:
    excluded = set(ML_TARGET_COLUMNS) | set(ML_PROVENANCE_COLUMNS)
    feature_cols = [col for col in ML_FEATURE_COLUMNS if col in df.columns]
    assert not excluded.intersection(feature_cols)
    x_df = df[feature_cols].copy()
    y = pd.to_numeric(df[target], errors="coerce").fillna(0.0)
    return x_df, y


def train_and_compare_target(
    df: pd.DataFrame,
    target: str,
) -> dict[str, Any]:
    """Train all candidate models for one target and select the best."""
    fit_train_df, val_df, test_df, cal_df, split_meta = time_aware_split(df)

    x_train, y_train = _prepare_xy(fit_train_df, target)
    x_val, y_val = _prepare_xy(val_df, target)
    x_test, y_test = _prepare_xy(test_df, target)
    x_cal, y_cal = _prepare_xy(cal_df, target)

    comparison_rows: list[dict[str, Any]] = []
    trained: dict[str, Any] = {}

    for model_name in MODEL_CANDIDATES:
        pipeline = build_model_pipeline(model_name)
        pipeline.fit(x_train, y_train)

        train_pred = pipeline.predict(x_train)
        val_pred = pipeline.predict(x_val)
        test_pred = pipeline.predict(x_test)

        train_metrics = regression_metrics(y_train, train_pred)
        val_metrics = regression_metrics(y_val, val_pred)
        test_metrics = regression_metrics(y_test, test_pred)

        conformal = ConformalIntervalEstimator(alpha=0.1)
        cal_pred = pipeline.predict(x_cal)
        conformal.fit(y_cal.to_numpy(), cal_pred)

        comparison_rows.append(
            {
                "model": model_name,
                "target": target,
                "train": train_metrics,
                "validation": val_metrics,
                "test": test_metrics,
                "overfitting_flag": overfitting_flag(train_metrics, val_metrics),
            }
        )

        trained[model_name] = {
            "pipeline": pipeline,
            "conformal": conformal,
            "train_metrics": train_metrics,
            "validation_metrics": val_metrics,
            "test_metrics": test_metrics,
        }

    best = min(
        comparison_rows,
        key=lambda row: row["validation"]["rmse"],
    )
    best_name = best["model"]
    selected = trained[best_name]

    return {
        "target": target,
        "split_metadata": split_meta.to_dict(),
        "selection_criterion": SELECTION_CRITERION,
        "selected_model": best_name,
        "comparison": comparison_rows,
        "pipeline": selected["pipeline"],
        "conformal": selected["conformal"],
        "selected_metrics": {
            "train": selected["train_metrics"],
            "validation": selected["validation_metrics"],
            "test": selected["test_metrics"],
        },
    }


def save_target_artifacts(target_result: dict[str, Any], model_dir: Path) -> None:
    """Persist selected pipeline, conformal estimator, and metadata."""
    target = target_result["target"]
    target_dir = model_dir / target
    target_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(target_result["pipeline"], target_dir / "pipeline.joblib")
    joblib.dump(target_result["conformal"], target_dir / "conformal.joblib")

    metadata = {
        "target": target,
        "selected_model": target_result["selected_model"],
        "selection_criterion": target_result["selection_criterion"],
        "split_metadata": target_result["split_metadata"],
        "selected_metrics": target_result["selected_metrics"],
        "comparison": target_result["comparison"],
        "feature_columns": list(ML_FEATURE_COLUMNS),
        "target_is_observed": False,
        "target_method": "impact_based_proxy_v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "uncertainty": target_result["conformal"].to_dict(),
    }
    with (target_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)


def train_all_models(
    dataset_path: Path | None = None,
    model_dir: Path | None = None,
) -> dict[str, Any]:
    """Train and save models for all four proxy targets."""
    dataset_path = dataset_path or (DATASET_DIR / "historical_ml_dataset.csv")
    model_dir = model_dir or MODEL_DIR
    model_dir.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading ML dataset from %s", dataset_path)
    df = pd.read_csv(dataset_path)
    logger.info("Training on %d records", len(df))

    results: dict[str, Any] = {
        "model_version": "milestone2_v1",
        "random_seed": RANDOM_SEED,
        "selection_criterion": SELECTION_CRITERION,
        "targets": {},
        "comparison_table": [],
    }

    for target in ML_TARGET_COLUMNS:
        logger.info("Training models for target: %s", target)
        target_result = train_and_compare_target(df, target)
        save_target_artifacts(target_result, model_dir)
        results["targets"][target] = {
            "selected_model": target_result["selected_model"],
            "selected_metrics": target_result["selected_metrics"],
            "split_metadata": target_result["split_metadata"],
            "uncertainty": target_result["conformal"].to_dict(),
        }
        for row in target_result["comparison"]:
            val_m = row["validation"]
            results["comparison_table"].append(
                {
                    "model": row["model"],
                    "target": row["target"],
                    "mae_train": row["train"]["mae"],
                    "rmse_train": row["train"]["rmse"],
                    "r2_train": row["train"]["r2"],
                    "mae_val": val_m["mae"],
                    "rmse_val": val_m["rmse"],
                    "r2_val": val_m["r2"],
                    "mae_test": row["test"]["mae"],
                    "rmse_test": row["test"]["rmse"],
                    "r2_test": row["test"]["r2"],
                    "overfitting_flag": row["overfitting_flag"],
                    "selected": row["model"] == target_result["selected_model"],
                }
            )

    registry_path = model_dir / "model_registry.json"
    report_path = REPORTS_DIR / "model_comparison_report.json"

    with registry_path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(results["comparison_table"], handle, indent=2)

    logger.info("Model training complete. Registry: %s", registry_path)
    return results
