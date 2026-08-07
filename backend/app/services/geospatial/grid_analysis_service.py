from shapely.geometry import Point, shape
from sqlalchemy.orm import Session

from app.models.building import Building
from app.services.geospatial.population_service import estimate_population
from app.services.resource_service import calculate_resources
from app.services.severity_service import calculate_severity


def analyze_grid(
    db: Session,
    grid_geojson: dict,
    radius_km: float,
) -> dict:
    """
    Analyze one disaster grid.

    Returns

    - Buildings
    - Population
    - Severity
    - Resource Requirement
    """

    polygon = shape(grid_geojson)

    minx, miny, maxx, maxy = polygon.bounds

    possible_buildings = (

        db.query(Building)

        .filter(

            Building.longitude >= minx,

            Building.longitude <= maxx,

            Building.latitude >= miny,

            Building.latitude <= maxy,

        )

        .all()

    )

    building_count = 0

    for building in possible_buildings:

        point = Point(

            building.longitude,

            building.latitude,

        )

        if polygon.contains(point):

            building_count += 1

    population = estimate_population(

        grid_geojson

    )["estimated_population"]

    severity = calculate_severity(

        population=population,

        building_count=building_count,

        radius_km=radius_km,

    )

    resources = calculate_resources(

        population,

        severity["severity_level"],

    )

    return {

        "building_count": building_count,

        "estimated_population": population,

        "severity_score": severity["severity_score"],

        "severity_level": severity["severity_level"],

        "food_packets": resources["food_packets"],

        "water_bottles": resources["water_bottles"],

        "medical_kits": resources["medical_kits"],

        "temporary_shelters": resources["temporary_shelters"],

    }