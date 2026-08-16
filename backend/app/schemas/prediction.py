"""Pydantic schemas for demand prediction API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VulnerabilityInput(BaseModel):
    elderly_ratio: float | None = Field(None, ge=0.0, le=1.0)
    children_ratio: float | None = Field(None, ge=0.0, le=1.0)
    medically_dependent_ratio: float | None = Field(None, ge=0.0, le=1.0)
    data_available: bool = False
    source: str = "unavailable"


class DemandFeatureInput(BaseModel):
    disaster_type_normalized: str
    event_year: int = Field(..., ge=1900, le=2100)
    event_month: int = Field(..., ge=1, le=12)
    state_normalized: str | None = None
    district_normalized: str | None = None
    deaths: int = 0
    injuries: int = 0
    missing_persons: int = 0
    affected_population: int = 0
    evacuated_population: int = 0
    houses_destroyed: int = 0
    houses_damaged: int = 0
    affected_families: int = 0
    relocated_population: int = 0
    hospitals_affected: int = 0
    schools_affected: int = 0
    agricultural_hectares: float = 0.0
    livestock_heads: int = 0
    road_damage_km: float = 0.0
    duration_days: int = 0
    sector_relief: int = 0
    sector_health: int = 0
    sector_education: int = 0
    sector_agriculture: int = 0
    sector_industry: int = 0
    sector_water: int = 0
    sector_sewer: int = 0
    sector_energy: int = 0
    sector_communications: int = 0
    sector_transport: int = 0


class DemandPredictionRequest(BaseModel):
    features: DemandFeatureInput
    severity_multiplier: float = Field(1.0, gt=0.0, le=10.0)
    vulnerability: VulnerabilityInput | None = None


class GridDemandPredictionRequest(BaseModel):
    grid_geojson: dict[str, Any]
    disaster_type: str
    estimated_population: int = 0
    building_count: int = 0
    severity_score: int = 0
    severity_level: str = "Moderate"
    severity_multiplier: float = Field(1.0, gt=0.0, le=10.0)
    vulnerability: VulnerabilityInput | None = None
    field_report_overrides: dict[str, Any] | None = None


class ScenarioPredictionRequest(BaseModel):
    features: DemandFeatureInput
    severity_multiplier: float = Field(1.0, gt=0.0, le=10.0)
    response_speed_factor: float = Field(1.0, gt=0.0, le=10.0)
    resource_availability_factor: float = Field(1.0, gt=0.0, le=10.0)
    vulnerability: VulnerabilityInput | None = None


class ZoneRecalculateRequest(BaseModel):
    severity_multiplier: float = Field(1.0, gt=0.0, le=10.0)
    vulnerability: VulnerabilityInput | None = None
    field_report_overrides: dict[str, Any] | None = None
    update_source: str = "field_report"
    satellite_placeholder: dict[str, Any] | None = None
