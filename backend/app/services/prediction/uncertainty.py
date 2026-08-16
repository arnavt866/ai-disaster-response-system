"""Split conformal prediction intervals for regression models."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ConformalIntervalEstimator:
    """
    Split conformal prediction intervals for point predictors.

    This provides prediction intervals, not classical confidence intervals.
  Coverage is approximate and depends on exchangeability of calibration data.
    """

    alpha: float = 0.1
    residual_quantile: float = 0.0
    method: str = "split_conformal_abs_residual"
    coverage_level: float = 0.9

    def fit(self, y_true: np.ndarray, y_pred: np.ndarray) -> "ConformalIntervalEstimator":
        residuals = np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))
        # Conformal quantile with finite-sample correction.
        n = len(residuals)
        if n == 0:
            self.residual_quantile = 0.0
            return self
        q_level = min(1.0, np.ceil((n + 1) * (1 - self.alpha)) / n)
        self.residual_quantile = float(np.quantile(residuals, q_level))
        self.coverage_level = 1.0 - self.alpha
        return self

    def predict_interval(self, point_predictions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        lower = np.maximum(0.0, point_predictions - self.residual_quantile)
        upper = point_predictions + self.residual_quantile
        return lower, upper

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "alpha": self.alpha,
            "coverage_level": self.coverage_level,
            "residual_quantile": self.residual_quantile,
            "interpretation": (
                "Prediction interval derived from absolute residuals on a "
                "held-out calibration split. This is not a classical "
                "confidence interval."
            ),
            "limitations": (
                "Assumes calibration and test data are exchangeable; "
                "coverage may degrade under distribution shift."
            ),
        }
