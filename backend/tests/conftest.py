"""Pytest DB isolation: outer transaction + SAVEPOINT so TestClient writes never persist.

By default this wraps the shared ``DATABASE_URL`` connection. Set
``TEST_DATABASE_URL`` to point at a dedicated Postgres database (PostGIS required)
instead; tables are created if missing. Either way, each test rolls back.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.connection import Base, engine as app_engine
from app.database.dependencies import get_db
from app.main import app
from app.api.auth_dependencies import require_commander
from app.models.commander import Commander
from app import models as _models  # noqa: F401 — register metadata for TEST_DATABASE_URL


def _test_engine():
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url:
        test_engine = create_engine(test_url)
        Base.metadata.create_all(bind=test_engine)
        return test_engine, True
    return app_engine, False


@pytest.fixture(autouse=True)
def _auth_bypass(request):
    """Bypass JWT on most tests; keep real auth checks in test_auth.py."""
    if "test_auth.py" in str(request.fspath):
        yield
        return

    def _fake_commander():
        return Commander(id=0, username="pytest", role="Commander", hashed_password="")

    app.dependency_overrides[require_commander] = _fake_commander
    yield
    app.dependency_overrides.pop(require_commander, None)


@pytest.fixture
def db_session(_db_savepoint_isolation):
    return _db_savepoint_isolation


@pytest.fixture(autouse=True)
def _db_savepoint_isolation():
    """Keep one Session per test; ``db.commit()`` only releases a SAVEPOINT."""
    engine, owns_engine = _test_engine()
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )

    def _override_get_db():
        try:
            yield session
        finally:
            session.expire_all()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()
        if owns_engine:
            engine.dispose()
