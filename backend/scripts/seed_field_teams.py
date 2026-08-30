"""One-time seed for a small set of realistic field teams.

Run once after clearing pytest-polluted rows:
    python scripts/seed_field_teams.py

Skips insert when a team_name already exists (safe to re-run without duplicating).
"""

from __future__ import annotations

from app.database.connection import SessionLocal
from app.models.field_team import FieldTeam

# Coordinates near active relief centers (Bhubaneswar / Delhi region depots).
FIELD_TEAMS = [
    {
        "team_name": "Alpha Response",
        "vehicle_type": "Truck",
        "vehicle_capacity": 5000,
        "contact_number": "+91-98765-10001",
        "base_latitude": 20.2961,
        "base_longitude": 85.8245,
    },
    {
        "team_name": "Bravo Rescue",
        "vehicle_type": "Van",
        "vehicle_capacity": 2000,
        "contact_number": "+91-98765-10002",
        "base_latitude": 20.3012,
        "base_longitude": 85.8310,
    },
    {
        "team_name": "Charlie Medical",
        "vehicle_type": "Ambulance",
        "vehicle_capacity": 800,
        "contact_number": "+91-98765-10003",
        "base_latitude": 20.2880,
        "base_longitude": 85.8180,
    },
    {
        "team_name": "Delta Relief",
        "vehicle_type": "Truck",
        "vehicle_capacity": 6000,
        "contact_number": "+91-98765-10004",
        "base_latitude": 28.6139,
        "base_longitude": 77.2090,
    },
    {
        "team_name": "Echo Supply",
        "vehicle_type": "Van",
        "vehicle_capacity": 1500,
        "contact_number": "+91-98765-10005",
        "base_latitude": 28.6200,
        "base_longitude": 77.2150,
    },
    {
        "team_name": "Foxtrot Logistics",
        "vehicle_type": "Truck",
        "vehicle_capacity": 4500,
        "contact_number": "+91-98765-10006",
        "base_latitude": 13.0827,
        "base_longitude": 80.2707,
    },
    {
        "team_name": "Gulf Rapid",
        "vehicle_type": "Van",
        "vehicle_capacity": 1800,
        "contact_number": "+91-98765-10007",
        "base_latitude": 13.0900,
        "base_longitude": 80.2780,
    },
    {
        "team_name": "Hotel Support",
        "vehicle_type": "Truck",
        "vehicle_capacity": 3500,
        "contact_number": "+91-98765-10008",
        "base_latitude": 20.3050,
        "base_longitude": 85.8400,
    },
    {
        "team_name": "India Care",
        "vehicle_type": "Ambulance",
        "vehicle_capacity": 600,
        "contact_number": "+91-98765-10009",
        "base_latitude": 28.6080,
        "base_longitude": 77.2000,
    },
    {
        "team_name": "Juliet Transit",
        "vehicle_type": "Van",
        "vehicle_capacity": 2200,
        "contact_number": "+91-98765-10010",
        "base_latitude": 20.2920,
        "base_longitude": 85.8100,
    },
]


def seed_field_teams(db) -> tuple[int, int]:
    """Insert seed teams; return (inserted_count, skipped_count)."""
    existing_names = {
        name
        for (name,) in db.query(FieldTeam.team_name).all()
    }
    inserted = 0
    skipped = 0
    for payload in FIELD_TEAMS:
        if payload["team_name"] in existing_names:
            skipped += 1
            continue
        db.add(FieldTeam(status="Available", **payload))
        inserted += 1
    if inserted:
        db.commit()
    return inserted, skipped


def main() -> None:
    db = SessionLocal()
    try:
        inserted, skipped = seed_field_teams(db)
        teams = db.query(FieldTeam).order_by(FieldTeam.id).all()
        print(f"Inserted {inserted} team(s), skipped {skipped} existing name(s).")
        print(f"field_teams row count: {len(teams)}")
        for team in teams:
            print(
                f"  id={team.id} {team.team_name!r} "
                f"status={team.status} vehicle={team.vehicle_type} cap={team.vehicle_capacity}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
