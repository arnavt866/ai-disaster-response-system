"""Authentication API tests."""

from fastapi.testclient import TestClient

from app.config.settings import DEFAULT_COMMANDER_PASSWORD, DEFAULT_COMMANDER_USERNAME
from app.main import app
from app.models.commander import Commander
from app.services.auth_service import hash_password

client = TestClient(app)


def test_login_rejects_invalid_password(db_session):
    db_session.add(
        Commander(
            username="auth_test_user",
            hashed_password=hash_password("correct-password"),
            role="Commander",
        )
    )
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"username": "auth_test_user", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_and_protected_route(db_session):
    db_session.add(
        Commander(
            username="auth_test_user2",
            hashed_password=hash_password("secret123"),
            role="Commander",
        )
    )
    db_session.commit()

    login = client.post(
        "/auth/login",
        json={"username": "auth_test_user2", "password": "secret123"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["username"] == "auth_test_user2"
    assert body["role"] == "Commander"
    token = body["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "auth_test_user2"

    protected = client.get("/zones/")
    assert protected.status_code == 401

    zones = client.get("/zones/", headers={"Authorization": f"Bearer {token}"})
    assert zones.status_code == 200


def test_default_commander_seeded(db_session):
    from app.services.auth_service import ensure_default_commander

    ensure_default_commander(db_session)
    commander = (
        db_session.query(Commander)
        .filter(Commander.username == DEFAULT_COMMANDER_USERNAME)
        .first()
    )
    assert commander is not None

    login = client.post(
        "/auth/login",
        json={
            "username": DEFAULT_COMMANDER_USERNAME,
            "password": DEFAULT_COMMANDER_PASSWORD,
        },
    )
    assert login.status_code == 200


def test_register_creates_account_and_returns_token(db_session):
    response = client.post(
        "/auth/register",
        json={"username": "new_ops_user", "password": "secure123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "new_ops_user"
    assert body["role"] == "Commander"
    assert body["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "new_ops_user"


def test_register_rejects_duplicate_username(db_session):
    db_session.add(
        Commander(
            username="taken_user",
            hashed_password=hash_password("existing-pass"),
            role="Commander",
        )
    )
    db_session.commit()

    response = client.post(
        "/auth/register",
        json={"username": "taken_user", "password": "another123"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already taken"


def test_register_validates_password_length(db_session):
    response = client.post(
        "/auth/register",
        json={"username": "short_pass_user", "password": "12345"},
    )
    assert response.status_code == 422
