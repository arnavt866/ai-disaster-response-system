"""JWT auth dependency for protected API routes."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.commander import Commander
from app.services.auth_service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def require_commander(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Commander:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    commander = (
        db.query(Commander)
        .filter(Commander.username == username)
        .first()
    )
    if commander is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Commander account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return commander
