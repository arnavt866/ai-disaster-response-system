import httpx
from sqlalchemy.orm import Session

from app.config.settings import (
    HTTP_CONNECT_TIMEOUT,
    HTTP_READ_TIMEOUT,
    OVERPASS_URL,
    SENTINEL_STAC_COLLECTION,
    SENTINEL_STAC_URL,
)
from app.services.geospatial.satellite_assessment_service import (
    CEMS_SOURCE_LABEL,
    query_satellite_assessments_at_point,
)

DEFAULT_OVERPASS_URL = "https://overpass.openstreetmap.ru/api/interpreter"
HTTP_TIMEOUT = httpx.Timeout(
    connect=HTTP_CONNECT_TIMEOUT,
    read=HTTP_READ_TIMEOUT,
    write=HTTP_CONNECT_TIMEOUT,
    pool=HTTP_CONNECT_TIMEOUT,
)

_PREVIEW_ASSET_KEYS = ("thumbnail", "rendered_preview", "overview", "visual")


def _preview_from_stac_item(item: dict) -> tuple[str | None, str | None]:
    """Return (href, asset_key) for the first usable preview asset on a STAC item."""
    assets = item.get("assets") or {}
    for key in _PREVIEW_ASSET_KEYS:
        href = (assets.get(key) or {}).get("href")
        if href:
            return href, key

    for link in item.get("links") or []:
        rel = str(link.get("rel", "")).lower()
        href = link.get("href")
        if href and rel in {"preview", "thumbnail"}:
            return href, rel
    return None, None


def _fetch_stac_item(collection: str, scene_id: str) -> dict | None:
    try:
        response = httpx.get(
            f"{SENTINEL_STAC_URL}/collections/{collection}/items/{scene_id}",
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        return None


def _cloud_cover_value(props: dict) -> float:
    value = props.get("eo:cloud_cover")
    try:
        return float(value) if value is not None else 999.0
    except (TypeError, ValueError):
        return 999.0


def _scene_record_from_feature(feature: dict, *, fetch_preview: bool = True) -> dict:
    props = feature.get("properties", {})
    scene_id = feature.get("id")
    preview_url, preview_asset = _preview_from_stac_item(feature)
    if fetch_preview and scene_id and not preview_url:
        item = _fetch_stac_item(SENTINEL_STAC_COLLECTION, scene_id)
        if item:
            preview_url, preview_asset = _preview_from_stac_item(item)

    return {
        "scene_id": scene_id,
        "datetime": props.get("datetime"),
        "cloud_cover_percent": props.get("eo:cloud_cover"),
        "platform": props.get("platform"),
        "preview_url": preview_url,
        "preview_asset": preview_asset,
    }


def _pick_best_scene(scenes: list[dict]) -> dict | None:
    if not scenes:
        return None
    return min(
        scenes,
        key=lambda scene: _cloud_cover_value(
            {"eo:cloud_cover": scene.get("cloud_cover_percent")}
        ),
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
    scenes = [_scene_record_from_feature(feature) for feature in features]
    best_scene = _pick_best_scene(scenes)

    return {
        "source": SENTINEL_STAC_URL,
        "collection": SENTINEL_STAC_COLLECTION,
        "scene_count": len(scenes),
        "scenes": scenes,
        "best_scene": best_scene,
        "preview_url": best_scene.get("preview_url") if best_scene else None,
        "preview_asset": best_scene.get("preview_asset") if best_scene else None,
    }


def get_damage_estimation(
    latitude: float,
    longitude: float,
    db: Session | None = None,
) -> dict:
    """
    Return observed CEMS mapping when the point intersects EMSR357 polygons.

    Outside that coverage, Sentinel-2 STAC scene metadata is returned and
    ``damage_level`` stays Unknown (no automated damage model).
    """
    if db is not None:
        cems = query_satellite_assessments_at_point(db, latitude, longitude)
        if cems is not None:
            return {
                "damage_level": cems["classification"] or "Observed",
                "status": "Copernicus EMS observed mapping available",
                "imagery_available": True,
                "source_label": CEMS_SOURCE_LABEL,
                "note": (
                    "Copernicus EMS observed mapping, Cyclone Fani 2019. "
                    "These polygons are analyst-produced Rapid Mapping products, "
                    "not AI-detected damage."
                ),
                "cems": cems,
            }

    try:
        scene_metadata = _query_sentinel_scene_metadata(latitude, longitude)
        return {
            "damage_level": "Unknown",
            "status": "Scene metadata available; damage assessment not implemented",
            "imagery_available": scene_metadata["scene_count"] > 0,
            "preview_url": scene_metadata.get("preview_url"),
            "preview_asset": scene_metadata.get("preview_asset"),
            "best_scene": scene_metadata.get("best_scene"),
            "scene_metadata": scene_metadata,
            "note": (
                "Sentinel-2 scene catalog entries were retrieved from a public "
                "STAC API. No damage scores are inferred from imagery. "
                "This location is outside imported Copernicus EMS EMSR357 coverage."
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
