"""FastAPI routes for Milestone-2 demand prediction."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.settings import MODEL_DIR, REPORTS_DIR
from app.database.dependencies import get_db
from app.schemas.prediction import (
    DemandPredictionRequest,
    GridDemandPredictionRequest,
    ScenarioPredictionRequest,
    ZoneRecalculateRequest,
)
from app.services.geospatial.grid_district_service import enrich_grid_with_districts
from app.services.prediction.demand_service import recalculate_grid_demand
from app.services.prediction.inference import (
    ModelArtifactsNotFoundError,
    load_model_registry,
    predict_demand,
)
from app.services.prediction.prediction_history import (
    load_prediction_history,
    record_prediction,
)
from app.services.prediction.scenario_service import simulate_demand_scenario
from app.services.prediction.vulnerability import VulnerabilityProfile
from app.services.prediction.zone_integration_service import predict_demand_for_zone

router = APIRouter(
    prefix="/prediction",
    tags=["Prediction"],
)


def _vulnerability_profile(payload) -> VulnerabilityProfile | None:
    if payload is None:
        return None
    return VulnerabilityProfile(
        elderly_ratio=payload.elderly_ratio,
        children_ratio=payload.children_ratio,
        medically_dependent_ratio=payload.medically_dependent_ratio,
        data_available=payload.data_available,
        source=payload.source,
    )


def _format_zone_level_response(
    zone_id: int | None,
    zone_name: str | None,
    prediction_payload: dict,
    extra: dict | None = None,
) -> dict:
    """Format zone-level demand with prediction intervals."""
    response = {
        "zone_id": zone_id,
        "zone_name": zone_name,
        "target_is_observed": prediction_payload.get("target_is_observed", False),
        "target_method": prediction_payload.get("target_method"),
        "model_version": prediction_payload.get("model_version"),
        "resource_estimates": prediction_payload.get("predictions", {}),
        "vulnerability": prediction_payload.get("vulnerability"),
        "severity_multiplier": prediction_payload.get("severity_multiplier", 1.0),
    }
    if extra:
        response.update(extra)
    return response


@router.get("/model")
def get_model_information():
    """Return trained model metadata and registry information."""
    try:
        registry = load_model_registry()
    except ModelArtifactsNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "model_version": registry.get("model_version"),
        "selection_criterion": registry.get("selection_criterion"),
        "target_is_observed": False,
        "target_method": "impact_based_proxy_v1",
        "targets": registry.get("targets", {}),
        "note": (
            "Resource-demand targets are proxy-derived from historical impact "
            "variables, not observed ground-truth consumption."
        ),
    }


@router.get("/evaluation")
def get_model_evaluation():
    """Return model comparison and evaluation metrics."""
    report_path = REPORTS_DIR / "model_comparison_report.json"
    registry_path = MODEL_DIR / "model_registry.json"

    if not report_path.exists() and not registry_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Model evaluation report not found. Train models first.",
        )

    payload: dict = {}
    if registry_path.exists():
        with registry_path.open(encoding="utf-8") as handle:
            payload["registry"] = json.load(handle)
    if report_path.exists():
        with report_path.open(encoding="utf-8") as handle:
            payload["comparison_table"] = json.load(handle)

    return payload


@router.get("/history")
def get_prediction_history(limit: int = 50):
    """Return recent prediction history for dynamic recalibration audit."""
    return {"entries": load_prediction_history(limit=limit)}


@router.post("/demand")
def predict_resource_demand(request: DemandPredictionRequest):
    """Predict proxy resource demand from feature inputs with prediction intervals."""
    try:
        result = predict_demand(
            features=request.features.model_dump(),
            severity_multiplier=request.severity_multiplier,
            vulnerability_profile=_vulnerability_profile(request.vulnerability),
        )
        registry = load_model_registry()
        record_prediction(
            zone_id=None,
            grid_reference=None,
            update_source="api_demand",
            model_version=registry.get("model_version"),
            predictions=result["predictions"],
            metadata={"features": request.features.model_dump()},
        )
        return _format_zone_level_response(None, None, result)
    except ModelArtifactsNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/demand/grid")
def predict_grid_demand(request: GridDemandPredictionRequest):
    """Predict demand for a current grid cell with district overlap integration."""
    overlaps = enrich_grid_with_districts(request.grid_geojson)
    grid_result = {
        "estimated_population": request.estimated_population,
        "building_count": request.building_count,
        "severity_score": request.severity_score,
        "severity_level": request.severity_level,
    }
    try:
        result = recalculate_grid_demand(
            grid_result=grid_result,
            disaster_type=request.disaster_type,
            district_overlaps=overlaps["overlaps"],
            severity_multiplier=request.severity_multiplier,
            vulnerability_profile=_vulnerability_profile(request.vulnerability),
            field_report_overrides=request.field_report_overrides,
        )
        registry = load_model_registry()
        record_prediction(
            zone_id=None,
            grid_reference="grid_cell",
            update_source="api_grid",
            model_version=registry.get("model_version"),
            predictions=result["prediction"]["predictions"],
            metadata={
                "disaster_type": request.disaster_type,
                "field_report_overrides": request.field_report_overrides,
            },
        )
        response = _format_zone_level_response(
            None,
            "grid_cell",
            result["prediction"],
            extra={
                "district_overlap": overlaps,
                "grid_features": result["grid_features"],
                "rule_based_resources": result["rule_based_resources"],
            },
        )
        return response
    except ModelArtifactsNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/demand/zone/{zone_id}")
def predict_zone_demand(
    zone_id: int,
    db: Session = Depends(get_db),
    request: ZoneRecalculateRequest | None = None,
):
    """
    Predict demand for an existing Milestone-1 DisasterZone.

    Uses M1 zone data and analyze_grid, then M2 model prediction with
    district polygon intersection.
    """
    req = request or ZoneRecalculateRequest()
    try:
        result = predict_demand_for_zone(
            db=db,
            zone_id=zone_id,
            severity_multiplier=req.severity_multiplier,
            vulnerability_profile=_vulnerability_profile(req.vulnerability),
            field_report_overrides=req.field_report_overrides,
            update_source=req.update_source,
            satellite_placeholder=req.satellite_placeholder,
        )
        return _format_zone_level_response(
            result["zone_id"],
            result["zone_name"],
            result["demand"]["prediction"],
            extra={
                "disaster_type": result["disaster_type"],
                "severity": result["severity"],
                "district_overlap": result["district_overlap"],
                "milestone1_grid_analysis": result["milestone1_grid_analysis"],
                "prediction_history_id": result["prediction_history_id"],
                "source": result["source"],
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelArtifactsNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/demand/zone/{zone_id}/recalculate")
def recalculate_zone_demand(
    zone_id: int,
    request: ZoneRecalculateRequest,
    db: Session = Depends(get_db),
):
    """
    Recalculate zone demand from updated field reports without retraining.

    Satellite input remains an optional placeholder only.
    """
    try:
        result = predict_demand_for_zone(
            db=db,
            zone_id=zone_id,
            severity_multiplier=request.severity_multiplier,
            vulnerability_profile=_vulnerability_profile(request.vulnerability),
            field_report_overrides=request.field_report_overrides,
            update_source=request.update_source,
            satellite_placeholder=request.satellite_placeholder,
        )
        return _format_zone_level_response(
            result["zone_id"],
            result["zone_name"],
            result["demand"]["prediction"],
            extra={
                "recalculated": True,
                "update_source": request.update_source,
                "field_report_overrides": request.field_report_overrides,
                "prediction_history_id": result["prediction_history_id"],
                "district_overlap": result["district_overlap"],
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelArtifactsNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/scenario")
def predict_scenario(request: ScenarioPredictionRequest):
    """Simulate demand under configurable scenario parameters."""
    try:
        return simulate_demand_scenario(
            features=request.features.model_dump(),
            severity_multiplier=request.severity_multiplier,
            response_speed_factor=request.response_speed_factor,
            resource_availability_factor=request.resource_availability_factor,
            vulnerability_profile=_vulnerability_profile(request.vulnerability),
        )
    except ModelArtifactsNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
