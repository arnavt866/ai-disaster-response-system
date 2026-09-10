"""Shared constants for Milestone 3 allocation and routing."""

from __future__ import annotations

M2_DEMAND_TARGETS: tuple[str, ...] = (
    "food_packets_demand",
    "water_demand",
    "medical_kits_demand",
    "shelter_capacity_demand",
)

DEMAND_TO_INVENTORY_CATEGORY: dict[str, str] = {
    "food_packets_demand": "food",
    "water_demand": "water",
    "medical_kits_demand": "medical",
    "shelter_capacity_demand": "shelter",
}

PRIORITY_WEIGHTS: dict[str, float] = {
    "Critical": 4.0,
    "High": 3.0,
    "Moderate": 2.0,
    "Low": 1.0,
}

MISSION_STATUSES: tuple[str, ...] = (
    "Created",
    "Allocated",
    "Dispatched",
    "In Transit",
    "Delivered",
)

ACTIVE_MISSION_STATUSES: tuple[str, ...] = (
    "Allocated",
    "Dispatched",
    "In Transit",
)

ASSIGNABLE_MISSION_STATUSES: tuple[str, ...] = tuple(
    status for status in MISSION_STATUSES if status != "Delivered"
)

AVAILABLE_FIELD_TEAM_STATUS = "Available"
INACTIVE_FIELD_TEAM_STATUS = "Inactive"

DEMAND_TARGET_DISPLAY_LABELS: dict[str, str] = {
    "food_packets_demand": "Food",
    "water_demand": "Water",
    "medical_kits_demand": "Medical",
    "shelter_capacity_demand": "Shelter",
}

AVG_TRUCK_SPEED_KPH = 60.0

# ASSUMPTION: daily payload a depot can move when no FieldTeam is linked to it.
# There is no relief_center_id FK on field_teams; this constant is the schema fallback.
DEFAULT_DEPOT_DAILY_PAYLOAD_KG = 10000.0

# ASSUMPTION: a field team with base lat/lon within this radius of a depot is
# treated as co-located with that depot's fleet. Not a database relationship.
TEAM_DEPOT_COLOCATION_KM = 15.0

# ASSUMPTION: kg per allocated demand unit. M2 estimates are counts (packets,
# bottles, kits, shelter units), not kilograms. These convert counts into the
# same mass unit as FieldTeam.vehicle_capacity / DEFAULT_DEPOT_DAILY_PAYLOAD_KG.
RESOURCE_UNIT_WEIGHT_KG: dict[str, float] = {
    "food": 0.5,  # ASSUMPTION: one food packet ≈ 0.5 kg
    "water": 1.0,  # ASSUMPTION: one water unit ≈ 1 L ≈ 1 kg
    "medical": 0.4,  # ASSUMPTION: one medical kit ≈ 0.4 kg
    "shelter": 2.0,  # ASSUMPTION: one shelter-capacity unit ≈ 2 kg of materials
}
