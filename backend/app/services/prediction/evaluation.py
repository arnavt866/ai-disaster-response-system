"""Model evaluation metrics and comparison helpers."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, float | None]:
    """Compute standard regression metrics."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(math.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))

    mape = None
    nonzero_mask = y_true != 0
    if nonzero_mask.any():
        mape = float(
            np.mean(
                np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])
            )
            * 100
        )

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "mape": mape,
    }


def overfitting_flag(
    train_metrics: dict[str, Any],
    test_metrics: dict[str, Any],
    r2_gap_threshold: float = 0.25,
) -> bool:
    """Flag suspicious generalization gaps."""
    train_r2 = train_metrics.get("r2")
    test_r2 = test_metrics.get("r2")
    if train_r2 is None or test_r2 is None:
        return False
    return (train_r2 - test_r2) > r2_gap_threshold
