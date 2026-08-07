from fastapi import APIRouter, Depends
from shapely.geometry import shape
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.disaster_zone_service import create_disaster_zones
from app.services.geospatial.grid_analysis_service import analyze_grid
from app.services.geospatial.grid_service import generate_grid
from app.services.geospatial.impact_service import compute_impact_area

router = APIRouter(
    prefix="/grid",
    tags=["Grid"],
)


@router.get("/generate")
def generate_disaster_grid(

    latitude: float,

    longitude: float,

    disaster_type: str,

    magnitude: float | None = None,

    alert_level: str | None = None,

    db: Session = Depends(get_db),

):

    impact = compute_impact_area(
        latitude=latitude,
        longitude=longitude,
        disaster_type=disaster_type,
        magnitude=magnitude,
        alert_level=alert_level,
    )

    polygon = shape(

        impact["polygon"]

    )

    cells = generate_grid(polygon)

    analyzed_cells = []

    total_population = 0
    total_buildings = 0
    total_food = 0
    total_water = 0
    total_medical = 0
    total_shelters = 0

    for cell in cells:

        result = analyze_grid(
            db=db,
            grid_geojson=cell.__geo_interface__,
            radius_km=impact["radius_km"],
        )

        analyzed_cells.append({

            "geometry": cell.__geo_interface__,

            **result

        })

        total_population += result["estimated_population"]
        total_buildings += result["building_count"]
        total_food += result["food_packets"]
        total_water += result["water_bottles"]
        total_medical += result["medical_kits"]
        total_shelters += result["temporary_shelters"]

    zones_saved = create_disaster_zones(

        db=db,

        disaster_type=disaster_type,

        analyzed_cells=analyzed_cells,

    )

    return {

        "radius_km": impact["radius_km"],

        "total_cells": len(cells),

        "zones_saved": zones_saved,

        "total_population": total_population,

        "total_buildings": total_buildings,

        "food_packets": total_food,

        "water_bottles": total_water,

        "medical_kits": total_medical,

        "temporary_shelters": total_shelters,

        "cells": analyzed_cells

    }