"""Tests for ML training and inference."""

from pathlib import Path

import pandas as pd
import pytest

from app.config.settings import DATASET_DIR, MODEL_DIR
from app.services.historical.feature_schema import (
    ML_FEATURE_COLUMNS,
    ML_PROVENANCE_COLUMNS,
    ML_TARGET_COLUMNS,
)
from app.services.prediction.inference import (
    ModelArtifactsNotFoundError,
    load_model_registry,
    predict_demand,
)
from app.services.prediction.preprocessing import build_preprocessor
from app.services.prediction.training import (
    _prepare_xy,
    build_model_pipeline,
    time_aware_split,
)


@pytest.fixture
def ml_dataset() -> pd.DataFrame:
    path = DATASET_DIR / "historical_ml_dataset.csv"
    assert path.exists()
    return pd.read_csv(path)


def test_feature_columns_exclude_targets_and_provenance(ml_dataset: pd.DataFrame):
    excluded = set(ML_TARGET_COLUMNS) | set(ML_PROVENANCE_COLUMNS)
    x_df, _ = _prepare_xy(ml_dataset, "food_packets_demand")
    assert not excluded.intersection(set(x_df.columns))
    assert list(x_df.columns) == list(ML_FEATURE_COLUMNS)


def test_time_aware_split_is_chronological(ml_dataset: pd.DataFrame):
    train, val, test, cal, meta = time_aware_split(ml_dataset)
    assert meta.strategy == "chronological_by_event_year"
    assert max(train["event_year"]) <= min(val["event_year"])
    assert len(train) > 0 and len(test) > 0


def test_model_pipeline_builds():
    pipeline = build_model_pipeline("ridge")
    preprocessor = pipeline.named_steps["preprocessor"]
    assert preprocessor is not None


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_model_registry_loads():
    registry = load_model_registry()
    assert registry["model_version"] == "milestone2_v1"
    assert len(registry["targets"]) == 4


@pytest.mark.skipif(
    not (MODEL_DIR / "model_registry.json").exists(),
    reason="Trained model artifacts not present",
)
def test_predict_demand_returns_intervals():
    features = {
        "disaster_type_normalized": "Flood",
        "event_year": 2020,
        "event_month": 6,
        "state_normalized": "Odisha",
        "district_normalized": "Cuttack",
        "affected_population": 1000,
        "injuries": 5,
    }
    result = predict_demand(features=features)
    assert result["target_is_observed"] is False
    for target in ML_TARGET_COLUMNS:
        assert target in result["predictions"]
        assert "prediction_interval_lower" in result["predictions"][target]
        assert "prediction_interval_upper" in result["predictions"][target]


def test_missing_artifacts_raises():
    with pytest.raises(ModelArtifactsNotFoundError):
        load_model_registry(str(Path("/nonexistent/models")))
