"""Live auth verification against configured DATABASE_URL."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config.settings import DEFAULT_COMMANDER_PASSWORD, DEFAULT_COMMANDER_USERNAME
from app.database.connection import SessionLocal
from app.database.dependencies import get_db
from app.main import app
from app.services.auth_service import ensure_default_commander


def _real_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def main() -> None:
    app.dependency_overrides[get_db] = _real_db
    client = TestClient(app)

    db = SessionLocal()
    try:
        ensure_default_commander(db)
    finally:
        db.close()

    print("=== INVALID PASSWORD ===")
    bad = client.post(
        "/auth/login",
        json={"username": DEFAULT_COMMANDER_USERNAME, "password": "wrong-password"},
    )
    print(f"status={bad.status_code} body={bad.json()}")

    print("\n=== VALID LOGIN ===")
    good = client.post(
        "/auth/login",
        json={
            "username": DEFAULT_COMMANDER_USERNAME,
            "password": DEFAULT_COMMANDER_PASSWORD,
        },
    )
    good.raise_for_status()
    token = good.json()["access_token"]
    print(json.dumps(good.json(), indent=2))

    print("\n=== PROTECTED WITHOUT TOKEN ===")
    denied = client.get("/zones/")
    print(f"status={denied.status_code}")

    print("\n=== PROTECTED WITH TOKEN ===")
    zones = client.get("/zones/", headers={"Authorization": f"Bearer {token}"})
    print(f"status={zones.status_code} zones={len(zones.json())}")

    print("\n=== LOGOUT ===")
    logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    print(f"status={logout.status_code} body={logout.json()}")


if __name__ == "__main__":
    main()
