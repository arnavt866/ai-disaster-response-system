import httpx

from app.config.settings import (
    HTTP_CONNECT_TIMEOUT,
    HTTP_READ_TIMEOUT,
    OVERPASS_URL,
    SENTINEL_STAC_COLLECTION,
    SENTINEL_STAC_URL,
)

DEFAULT_OVERPASS_URL = "https://overpass.openstreetmap.ru/api/interpreter"
HTTP_TIMEOUT = httpx.Timeout(
    connect=HTTP_CONNECT_TIMEOUT,
    read=HTTP_READ_TIMEOUT,
    write=HTTP_CONNECT_TIMEOUT,
    pool=HTTP_CONNECT_TIMEOUT,
)


def get_nearby_facilities(
    latitude: float,
    longitude: float,
    radius: int = 5000,
) -> dict:
    """Fetch nearby emergency facilities from OpenStreetMap via Overpass."""
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
            OVERPASS_URL or DEFAULT_OVERPASS_URL,
            data=query,
            headers={"Content-Type": "text/plain"},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return {
            "status": "Service Unavailable",
            "message": "OpenStreetMap Overpass server is currently unavailable.",
            "count": 0,
            "facilities": [],
        }

    facilities = []
    for place in response.json().get("elements", []):
        facilities.append(
            {
                "name": place.get("tags", {}).get("name", "Unknown"),
                "type": place.get("tags", {}).get("amenity", "Unknown"),
                "latitude": place.get("lat"),
                "longitude": place.get("lon"),
            }
        )

    return {
        "status": "Success",
        "count": len(facilities),
        "facilities": facilities,
    }


def _query_sentinel_scene_metadata(
    latitude: float,
    longitude: float,
    *,
    bbox_buffer: float = 0.05,
    limit: int = 3,
) -> dict:
    """
    Query public Sentinel-2 STAC metadata for the area.

    Returns scene availability only. No damage scores are inferred from imagery.
    """
    min_lon = longitude - bbox_buffer
    min_lat = latitude - bbox_buffer
    max_lon = longitude + bbox_buffer
    max_lat = latitude + bbox_buffer
    bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"

    response = httpx.get(
        f"{SENTINEL_STAC_URL}/collections/{SENTINEL_STAC_COLLECTION}/items",
        params={"bbox": bbox, "limit": limit},
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()

    features = response.json().get("features", [])
    scenes = []
    for feature in features:
        props = feature.get("properties", {})
        scenes.append(
            {
                "scene_id": feature.get("id"),
                "datetime": props.get("datetime"),
                "cloud_cover_percent": props.get("eo:cloud_cover"),
                "platform": props.get("platform"),
            }
        )

    return {
        "source": SENTINEL_STAC_URL,
        "collection": SENTINEL_STAC_COLLECTION,
        "scene_count": len(scenes),
        "scenes": scenes,
    }


def get_damage_estimation(
    latitude: float,
    longitude: float,
) -> dict:
    """
    Return satellite scene metadata when available.

    Damage assessment is not automated. `damage_level` remains Unknown because
    no validated damage model is integrated in Milestone 1/2.
    """
    try:
        scene_metadata = _query_sentinel_scene_metadata(latitude, longitude)
        return {
            "damage_level": "Unknown",
            "status": "Scene metadata available; damage assessment not implemented",
            "imagery_available": scene_metadata["scene_count"] > 0,
            "scene_metadata": scene_metadata,
            "note": (
                "Sentinel-2 scene catalog entries were retrieved from a public "
                "STAC API. No damage scores are inferred from imagery."
            ),
        }
    except httpx.HTTPError as exc:
        return {
            "damage_level": "Unknown",
            "status": "Satellite catalog unavailable",
            "imagery_available": False,
            "message": str(exc),
            "note": (
                "Public Sentinel STAC lookup failed. Rule-based impact estimation "
                "and ML demand prediction remain available."
            ),
        }
