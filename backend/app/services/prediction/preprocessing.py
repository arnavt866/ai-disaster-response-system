"""Feature preprocessing for demand prediction models."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.services.historical.feature_schema import ML_FEATURE_COLUMNS

NUMERIC_FEATURES: tuple[str, ...] = tuple(
    col
    for col in ML_FEATURE_COLUMNS
    if col
    not in {
        "disaster_type_normalized",
        "state_normalized",
        "district_normalized",
    }
)

CATEGORICAL_FEATURES: tuple[str, ...] = (
    "disaster_type_normalized",
    "state_normalized",
    "district_normalized",
)


def build_preprocessor(scale_numeric: bool = False) -> ColumnTransformer:
    """Build a sklearn preprocessor for model features."""
    numeric_steps: list[tuple[str, object]] = [
        ("imputer", SimpleImputer(strategy="median")),
    ]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(numeric_steps), list(NUMERIC_FEATURES)),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(CATEGORICAL_FEATURES),
            ),
        ],
        remainder="drop",
    )
