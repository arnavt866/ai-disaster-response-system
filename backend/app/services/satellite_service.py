import httpx

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"


def get_nearby_facilities(
    latitude: float,
    longitude: float,
    radius: int = 5000
):
    """
    Fetch nearby emergency facilities using OpenStreetMap Overpass API.
    """

    query = f"""
    [out:json];

    node
        ["amenity"="hospital"]
    (around:{radius},{latitude},{longitude});

    out body;
    """

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
            pool=20
        )
    )  

    response.raise_for_status()

    data = response.json()

    results = []

    for place in data.get("elements", []):

        results.append({

            "name": place.get("tags", {}).get(
                "name",
                "Unknown"
            ),

            "type": place.get("tags", {}).get(
                "amenity"
            ),

            "latitude": place.get("lat"),

            "longitude": place.get("lon")

        })

    return results

def get_damage_estimation(
    latitude: float,
    longitude: float
):
    """
    Placeholder.

    Later this will combine

    - Satellite imagery
    - Building footprints
    - Damage estimation

    """

    return {

        "damage_level": "Unknown",

        "status":
            "Satellite module under development"

    }