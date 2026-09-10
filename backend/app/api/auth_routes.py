"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_dependencies import require_commander
from app.database.dependencies import get_db
from app.models.commander import Commander
from app.schemas.auth import CommanderResponse, LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    authenticate_commander,
    create_access_token,
    register_commander,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    commander = authenticate_commander(db, request.username, request.password)
    if commander is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=commander.username, role=commander.role)
    return TokenResponse(
        access_token=token,
        username=commander.username,
        role=commander.role,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(Commander)
        .filter(Commander.username == request.username)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    commander = register_commander(db, request.username, request.password)
    token = create_access_token(subject=commander.username, role=commander.role)
    return TokenResponse(
        access_token=token,
        username=commander.username,
        role=commander.role,
    )


@router.get("/me", response_model=CommanderResponse)
def read_current_commander(commander: Commander = Depends(require_commander)):
    return commander


@router.post("/logout")
def logout(_commander: Commander = Depends(require_commander)):
    """Stateless JWT logout — client discards the token."""
    return {"message": "Logged out"}
