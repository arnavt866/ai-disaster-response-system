"""
Impact Assessment Service

This module combines information from multiple sources
to estimate the overall impact of a disaster.

Future integrations:
- USGS
- GDACS
- NDMA
- Satellite imagery
- Population density
- OpenStreetMap
"""

from app.services.population_service import estimate_population
from app.services.satellite_service import get_damage_estimation
from app.services.osm_service import get_nearby_buildings
from app.services.grid_service import classify_zone


def assess_disaster_impact(disaster: dict):
    """
    Generate a simple impact report.

    More components will be added later without changing
    the API structure.
    """

    latitude = disaster["latitude"]
    longitude = disaster["longitude"]

    report = {

        "event_id": disaster["event_id"],

        "title": disaster["title"],

        "location": disaster["location"],

        "severity": disaster["severity"],

        "population_estimate":
            estimate_population(
                latitude,
                longitude
            ),

        "satellite_assessment":
            get_damage_estimation(
                latitude,
                longitude
            ),

        "nearby_infrastructure":
            get_nearby_buildings(
                latitude,
                longitude
            ),

        "grid_information":
            classify_zone(
                latitude,
                longitude,
                disaster["severity"]
            )

    }

    return report