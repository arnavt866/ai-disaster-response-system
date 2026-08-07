import requests
from shapely.geometry import Polygon, shape

from app.core.logger import logger

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def get_buildings(
    polygon: Polygon,
) -> list[Polygon]:
    """
    Retrieve building footprints inside the
    given disaster polygon using the
    Overpass API.
    """

    coords = list(polygon.exterior.coords)

    polygon_string = " ".join(
        f"{lat} {lon}"
        for lon, lat in coords
    )

    query = f"""
    [out:json][timeout:20];

    (
    way["building"](poly:"{polygon_string}");
    );

    out body;
    """

    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        timeout=90,
    )
    logger.debug(
        f"Overpass response: {response.status_code}"
    )   
    response.raise_for_status()

    data = response.json()
                                                                                                                
    buildings = []

    for element in data.get("elements", []):

        if "geometry" not in element:
            continue

        coordinates = [
            (point["lon"], point["lat"])
            for point in element["geometry"]
        ]

        try:

            poly = Polygon(coordinates)

            if poly.is_valid:

                buildings.append(poly)

        except Exception as e:

            logger.warning(
                f"Invalid building polygon skipped: {e}"
            )

            continue

    return buildings