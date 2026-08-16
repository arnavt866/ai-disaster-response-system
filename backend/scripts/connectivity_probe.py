"""Bounded external connectivity probe for audit (not used in production)."""

from __future__ import annotations

import json
import sys

import httpx

LAT, LON = 20.2, 85.8
BBOX = f"{LON},{LAT},{LON + 0.1},{LAT + 0.1}"


def probe() -> dict:
    results: dict = {}

    try:
        response = httpx.get(
            "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items",
            params={"bbox": BBOX, "limit": 1},
            timeout=15.0,
        )
        if response.status_code == 200:
            features = response.json().get("features", [])
            item = features[0] if features else {}
            props = item.get("properties", {})
            results["earthsearch_stac"] = {
                "status": 200,
                "scene_count": len(features),
                "sample_datetime": props.get("datetime"),
                "sample_cloud_cover": props.get("eo:cloud_cover"),
            }
        else:
            results["earthsearch_stac"] = {
                "status": response.status_code,
                "body": response.text[:200],
            }
    except Exception as exc:
        results["earthsearch_stac"] = {"error": str(exc)[:200]}

    try:
        response = httpx.get(
            "https://catalogue.dataspace.copernicus.eu/stac/collections/sentinel-2-l2a/items",
            params={"bbox": BBOX, "limit": 1},
            timeout=15.0,
        )
        results["copernicus_stac"] = {
            "status": response.status_code,
            "body": response.text[:200],
        }
    except Exception as exc:
        results["copernicus_stac"] = {"error": str(exc)[:200]}

    try:
        response = httpx.get(
            "https://sachet.ndma.gov.in/",
            timeout=15.0,
            follow_redirects=True,
        )
        results["ndma_portal"] = {
            "status": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "html_length": len(response.text),
        }
    except Exception as exc:
        results["ndma_portal"] = {"error": str(exc)[:200]}

    for path in ("/api/alerts", "/api/v1/alerts", "/cap/alerts", "/rss/alerts"):
        url = f"https://sachet.ndma.gov.in{path}"
        try:
            response = httpx.get(url, timeout=10.0, follow_redirects=True)
            results[f"ndma{path}"] = {
                "status": response.status_code,
                "content_type": response.headers.get("content-type", "")[:60],
            }
        except Exception as exc:
            results[f"ndma{path}"] = {"error": str(exc)[:100]}

    try:
        query = (
            f'[out:json];node["amenity"="hospital"]'
            f"(around:1000,{LAT},{LON});out count;"
        )
        response = httpx.post(
            "https://overpass.openstreetmap.ru/api/interpreter",
            data=query,
            timeout=20.0,
        )
        results["overpass"] = {"status": response.status_code}
    except Exception as exc:
        results["overpass"] = {"error": str(exc)[:200]}

    return results


if __name__ == "__main__":
    sys.stdout.write(json.dumps(probe(), indent=2))
