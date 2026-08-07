import httpx

OVERPASS_URL = "https://overpass.openstreetmap.ru/api/interpreter"


def get_nearby_facilities(
    latitude: float,
    longitude: float,
    radius: int = 5000,
) -> dict:
    """
    Fetch nearby hospitals from OpenStreetMap using the Overpass API.
    """

    query = f"""
    [out:json];

    (
        node["amenity"="hospital"](around:{radius},{latitude},{longitude});
        node["amenity"="police"](around:{radius},{latitude},{longitude});
        node["amenity"="fire_station"](around:{radius},{latitude},{longitude});
        node["amenity"="shelter"](around:{radius},{latitude},{longitude});
    );

    out body;
    """

    try:

        response = httpx.post(
            OVERPASS_URL,
            data=query,
            headers={
                "Content-Type": "text/plain"
            },
            timeout=httpx.Timeout(
                connect=20,
                read=180,
                write=20,
                pool=20,
            ),
        )

        response.raise_for_status()

    except httpx.HTTPError:

        return {
            "status": "Service Unavailable",
            "message": (
                "OpenStreetMap Overpass server is currently unavailable."
            ),
            "count": 0,
            "facilities": [],
        }

    data = response.json()

    facilities = []

    for place in data.get("elements", []):

        facilities.append({

            "name": place.get("tags", {}).get(
                "name",
                "Unknown"
            ),

            "type": place.get("tags", {}).get(
                "amenity",
                "Unknown"
            ),

            "latitude": place.get("lat"),

            "longitude": place.get("lon"),

        })

    return {

        "status": "Success",

        "count": len(facilities),

        "facilities": facilities,

    }


def get_damage_estimation(
    latitude: float,
    longitude: float,
) -> dict:
    """
    Placeholder for the future satellite damage assessment module.
    """

    return {

        "damage_level": "Unknown",

        "status": "Satellite module under development",

    }