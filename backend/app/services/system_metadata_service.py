"""Workflow metadata exposed to the frontend (single source of truth)."""

from __future__ import annotations

from app.services.optimization.constants import (
    ACTIVE_MISSION_STATUSES,
    ASSIGNABLE_MISSION_STATUSES,
    AVAILABLE_FIELD_TEAM_STATUS,
    DEMAND_TARGET_DISPLAY_LABELS,
    DEMAND_TO_INVENTORY_CATEGORY,
    INACTIVE_FIELD_TEAM_STATUS,
    M2_DEMAND_TARGETS,
    MISSION_STATUSES,
    PRIORITY_WEIGHTS,
)
from app.services.optimization.resource_tracking_service import VALID_TRANSITIONS


def get_system_metadata() -> dict:
    """Return domain enums and mappings used by the UI workflow."""
    operational_priorities = sorted(
        PRIORITY_WEIGHTS.keys(),
        key=lambda name: PRIORITY_WEIGHTS[name],
        reverse=True,
    )
    mission_transitions = {
        status: sorted(next_statuses)
        for status, next_statuses in VALID_TRANSITIONS.items()
    }
    demand_targets = [
        {
            "target": target,
            "display_label": DEMAND_TARGET_DISPLAY_LABELS[target],
            "inventory_category": DEMAND_TO_INVENTORY_CATEGORY[target],
        }
        for target in M2_DEMAND_TARGETS
    ]
    return {
        "operational_priorities": operational_priorities,
        "mission_statuses": list(MISSION_STATUSES),
        "mission_transitions": mission_transitions,
        "active_mission_statuses": list(ACTIVE_MISSION_STATUSES),
        "assignable_mission_statuses": list(ASSIGNABLE_MISSION_STATUSES),
        "available_field_team_status": AVAILABLE_FIELD_TEAM_STATUS,
        "inactive_field_team_status": INACTIVE_FIELD_TEAM_STATUS,
        "demand_targets": demand_targets,
        "data_source": "backend_constants",
    }
