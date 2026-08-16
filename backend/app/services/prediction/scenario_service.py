"""Scenario simulation for demand prediction."""

from __future__ import annotations

from typing import Any

from app.services.prediction.inference import predict_demand
from app.services.prediction.vulnerability import VulnerabilityProfile


def simulate_demand_scenario(
    features: dict[str, Any],
    severity_multiplier: float = 1.0,
    response_speed_factor: float = 1.0,
    resource_availability_factor: float = 1.0,
    vulnerability_profile: VulnerabilityProfile | None = None,
) -> dict[str, Any]:
    """
    Simulate demand under configurable scenario assumptions.

    Scenario multipliers adjust predicted demand without retraining the model.
    resource_availability_factor is returned for planning context only.
    """
    effective_severity = severity_multiplier / max(response_speed_factor, 0.01)
    result = predict_demand(
        features=features,
        severity_multiplier=effective_severity,
        vulnerability_profile=vulnerability_profile,
    )

    adjusted_predictions: dict[str, Any] = {}
    for target, payload in result["predictions"].items():
        scale = 1.0 / max(resource_availability_factor, 0.01)
        adjusted_predictions[target] = {
            **payload,
            "scenario_adjusted_estimate": int(
                round(payload["point_estimate"] * scale)
            ),
        }

    return {
        **result,
        "predictions": adjusted_predictions,
        "scenario_parameters": {
            "severity_multiplier": severity_multiplier,
            "response_speed_factor": response_speed_factor,
            "resource_availability_factor": resource_availability_factor,
            "effective_severity_multiplier": round(effective_severity, 4),
        },
        "note": (
            "Scenario outputs are simulation results based on the trained "
            "proxy-demand model and configurable multipliers. They are not "
            "observed historical resource consumption."
        ),
    }
