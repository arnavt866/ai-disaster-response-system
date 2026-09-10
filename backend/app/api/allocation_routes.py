"""Milestone 3 allocation and priority routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.allocation_record import AllocationRecord
from app.schemas.allocation import (
    AllocationRunRequest,
    PriorityOverrideRequest,
    RoadBlockClearRequest,
    RoadBlockRequest,
    RouteRequest,
)
from app.services.optimization.allocation_service import optimize_allocation, update_zone_priority
from app.services.optimization.road_block_store import (
    add_blocked_edge,
    clear_blocked_edges,
    list_blocked_edges,
    remove_blocked_edge,
)
from app.services.optimization.routing_service import build_road_route
from app.services.relief_service import get_relief_center_by_id
from app.services.zone_service import get_zone_by_id

router = APIRouter(prefix="/allocation", tags=["Allocation"])


@router.get("/status")
def allocation_status():
    return {
        "optimizer": "online",
        "algorithm": "ortools_glop_priority_transportation",
        "description": (
            "Priority-weighted linear program using M2 zone demand and "
            "relief-center inventory supply."
        ),
    }


DEFAULT_UNBOUNDED_SANITY_CAP = 100


@router.post("/optimize")
def run_allocation(request: AllocationRunRequest, db: Session = Depends(get_db)):
    is_unbounded = request.zone_ids is None or len(request.zone_ids) == 0
    if is_unbounded and not request.confirm_all_zones:
        raise HTTPException(
            status_code=400,
            detail=(
                "Full-system allocation across all disaster zones requires explicit confirmation "
                "to prevent accidental long-running full-system optimization. "
                "Please specify target 'zone_ids' (e.g. [1, 2]) or set 'confirm_all_zones: true'."
            ),
        )

    effective_cap = request.max_zones
    if is_unbounded and effective_cap is None:
        effective_cap = DEFAULT_UNBOUNDED_SANITY_CAP

    try:
        result = optimize_allocation(
            db,
            request.zone_ids,
            persist=request.persist,
            max_zones=effective_cap if is_unbounded else None,
            allow_unbounded=is_unbounded and request.confirm_all_zones,
        )
        if is_unbounded:
            result["warning"] = (
                f"Full-system optimization executed for {result.get('zone_count', 0)} zones "
                f"(capped at {effective_cap} zones)."
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/history")
def allocation_history(limit: int = 100, db: Session = Depends(get_db)):
    rows = (
        db.query(AllocationRecord)
        .order_by(AllocationRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "total": len(rows),
        "records": [
            {
                "id": row.id,
                "run_id": row.run_id,
                "zone_id": row.zone_id,
                "relief_center_id": row.relief_center_id,
                "resource_category": row.resource_category,
                "demanded": row.demanded,
                "allocated": row.allocated,
                "unmet": row.unmet,
                "priority_weight": row.priority_weight,
                "optimization_status": row.optimization_status,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/zones/{zone_id}/priority")
def override_zone_priority(
    zone_id: int,
    request: PriorityOverrideRequest,
    db: Session = Depends(get_db),
):
    try:
        zone = update_zone_priority(db, zone_id, request.priority)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "zone_id": zone.id,
        "operational_priority": zone.operational_priority,
        "message": "Priority updated. Re-run allocation to apply.",
    }


@router.post("/zones/{zone_id}/recalculate")
def recalculate_after_priority(
    zone_id: int,
    db: Session = Depends(get_db),
):
    return optimize_allocation(db, [zone_id], persist=True)


@router.post("/route")
def compute_route(request: RouteRequest, db: Session = Depends(get_db)):
    zone = get_zone_by_id(db, request.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    depot = get_relief_center_by_id(db, request.relief_center_id)
    if depot is None:
        raise HTTPException(status_code=404, detail="Relief center not found")
    return build_road_route(
        depot_id=depot.id,
        depot_name=depot.name,
        depot_lat=depot.latitude,
        depot_lon=depot.longitude,
        zone_id=zone.id,
        zone_name=zone.zone_name,
        zone_lat=zone.latitude,
        zone_lon=zone.longitude,
        blocked=request.blocked,
    )


@router.get("/road-blocks")
def get_road_blocks(region_id: str | None = None):
    return {"blocks": list_blocked_edges(region_id)}


@router.post("/road-blocks")
def create_road_block(request: RoadBlockRequest):
    if request.region_id not in {"chennai", "bhubaneswar", "delhi"}:
        raise HTTPException(status_code=400, detail="Unknown demo region_id")
    entry = add_blocked_edge(request.region_id, request.u, request.v)
    return {"message": "Road segment marked blocked.", "block": entry}


@router.delete("/road-blocks")
def delete_road_block(request: RoadBlockRequest):
    removed = remove_blocked_edge(request.region_id, request.u, request.v)
    if not removed:
        raise HTTPException(status_code=404, detail="Blocked edge not found")
    return {"message": "Road segment unblocked."}


@router.post("/road-blocks/clear")
def clear_road_blocks(request: RoadBlockClearRequest):
    removed = clear_blocked_edges(request.region_id)
    return {
        "message": "Road blocks cleared.",
        "removed_count": removed,
        "region_id": request.region_id,
    }
