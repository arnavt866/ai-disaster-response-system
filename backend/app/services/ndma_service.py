import httpx

from app.config.settings import (
    HTTP_CONNECT_TIMEOUT,
    HTTP_READ_TIMEOUT,
    NDMA_PORTAL_URL,
)

HTTP_TIMEOUT = httpx.Timeout(
    connect=HTTP_CONNECT_TIMEOUT,
    read=HTTP_READ_TIMEOUT,
    write=HTTP_CONNECT_TIMEOUT,
    pool=HTTP_CONNECT_TIMEOUT,
)


def fetch_ndma_events() -> dict:
    """
    NDMA SACHET is a web portal without a documented public disaster-alert REST API.

    Connectivity audit (2026-08-17): portal HTML reachable; common REST paths
    `/api/alerts`, `/api/v1/alerts`, `/cap/alerts`, `/rss/alerts` returned 404.
    """
    portal_status = None
    portal_reachable = False
    try:
        response = httpx.get(
            NDMA_PORTAL_URL,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        )
        portal_status = response.status_code
        portal_reachable = response.status_code < 500
    except httpx.HTTPError as exc:
        portal_status = f"unreachable: {exc}"

    return {
        "status": "Not Implemented",
        "source": "NDMA",
        "portal_url": NDMA_PORTAL_URL,
        "portal_reachable": portal_reachable,
        "portal_status": portal_status,
        "message": (
            "No official public NDMA disaster-alert REST API is available for "
            "automated ingestion. Set NDMA_URL when an authenticated feed is "
            "provided by NDMA."
        ),
    }
