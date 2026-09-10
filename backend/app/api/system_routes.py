"""System metadata routes for frontend workflow configuration."""

from fastapi import APIRouter

from app.services.system_metadata_service import get_system_metadata

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/metadata")
def system_metadata():
    """Return domain enums and mappings (priorities, mission workflow, demand targets)."""
    return get_system_metadata()
