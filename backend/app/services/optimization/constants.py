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

AVG_TRUCK_SPEED_KPH = 60.0
