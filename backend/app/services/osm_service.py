"""
OpenStreetMap Service

Responsible for fetching nearby infrastructure
such as hospitals, shelters and police stations.

Currently returns placeholder data.

Later this service will connect to
OpenStreetMap Overpass API.
"""


def get_nearby_buildings(
    latitude: float,
    longitude: float,
    radius: int = 5000
):

    return {

        "status":
            "OpenStreetMap integration pending",

        "latitude":
            latitude,

        "longitude":
            longitude,

        "radius":
            radius,

        "buildings": []

    }