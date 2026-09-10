"""Password hashing and JWT helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config.settings import (
    DEFAULT_COMMANDER_PASSWORD,
    DEFAULT_COMMANDER_USERNAME,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)
from app.models.commander import Commander

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_commander(
    db: Session,
    username: str,
    password: str,
) -> Commander | None:
    commander = (
        db.query(Commander)
        .filter(Commander.username == username)
        .first()
    )
    if commander is None or not verify_password(password, commander.hashed_password):
        return None
    return commander


def register_commander(db: Session, username: str, password: str) -> Commander:
    """Create a new commander account. Caller must handle duplicate usernames."""
    commander = Commander(
        username=username,
        hashed_password=hash_password(password),
        role="Commander",
    )
    db.add(commander)
    db.commit()
    db.refresh(commander)
    return commander


def create_access_token(*, subject: str, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def ensure_default_commander(db: Session) -> Commander | None:
    """Create the default commander account when none exists for that username."""
    existing = (
        db.query(Commander)
        .filter(Commander.username == DEFAULT_COMMANDER_USERNAME)
        .first()
    )
    if existing is not None:
        return existing

    commander = Commander(
        username=DEFAULT_COMMANDER_USERNAME,
        hashed_password=hash_password(DEFAULT_COMMANDER_PASSWORD),
        role="Commander",
    )
    db.add(commander)
    db.commit()
    db.refresh(commander)
    return commander
