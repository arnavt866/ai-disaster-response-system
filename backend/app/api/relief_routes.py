from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.relief_center import ReliefCenterCreate, ReliefCenterResponse
from app.services.relief_service import (
    create_relief_center,
    delete_relief_center,
    get_all_relief_centers,
    get_relief_center_by_id,
    update_relief_center,
)

router = APIRouter(
    prefix="/relief-centers",
    tags=["Relief Centers"]
)





@router.post("/", response_model=ReliefCenterResponse)
def create_center(
    center: ReliefCenterCreate,
    db: Session = Depends(get_db)
):
    return create_relief_center(db, center)


@router.get("/", response_model=list[ReliefCenterResponse])
def get_centers(db: Session = Depends(get_db)):
    return get_all_relief_centers(db)

@router.get("/{center_id}", response_model=ReliefCenterResponse)
def get_center_by_id(
    center_id: int,
    db: Session = Depends(get_db)
):

    center = get_relief_center_by_id(
        db,
        center_id
    )

    if center is None:

        raise HTTPException(
            status_code=404,
            detail="Relief Center not found"
        )

    return center

@router.put("/{center_id}", response_model=ReliefCenterResponse)
def update_center(
    center_id: int,
    updated_center: ReliefCenterCreate,
    db: Session = Depends(get_db)
):

    center = update_relief_center(
        db,
        center_id,
        updated_center
    )

    if center is None:

        raise HTTPException(
            status_code=404,
            detail="Relief Center not found"
        )

    return center

@router.delete("/{center_id}", response_model=ReliefCenterResponse)
def delete_center(
    center_id: int,
    db: Session = Depends(get_db)
):

    center = delete_relief_center(
        db,
        center_id
    )

    if center is None:

        raise HTTPException(
            status_code=404,
            detail="Relief Center not found"
        )

    return center