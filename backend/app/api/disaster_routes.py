from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db

from app.schemas.disaster_event import (
    DisasterEventCreate,
    DisasterEventResponse
)

from app.services.disaster_service import (
    create_disaster,
    get_all_disasters,
    get_disaster_by_id,
    update_disaster,
    delete_disaster
)

router = APIRouter(
    prefix="/disasters",
    tags=["Disaster Events"]
)





@router.post("/", response_model=DisasterEventResponse)

def create_disaster_event(
        disaster: DisasterEventCreate,
        db: Session = Depends(get_db)
):

    return create_disaster(db, disaster)


@router.get("/", response_model=list[DisasterEventResponse])

def get_disasters(
        db: Session = Depends(get_db)
):

    return get_all_disasters(db)

@router.get("/{disaster_id}", response_model=DisasterEventResponse)
def get_disaster(
    disaster_id: int,
    db: Session = Depends(get_db)
):

    disaster = get_disaster_by_id(
        db,
        disaster_id
    )

    if disaster is None:

        raise HTTPException(
            status_code=404,
            detail="Disaster Event not found"
        )

    return disaster

@router.put("/{disaster_id}", response_model=DisasterEventResponse)
def update_disaster_event(
    disaster_id: int,
    updated_disaster: DisasterEventCreate,
    db: Session = Depends(get_db)
):

    disaster = update_disaster(
        db,
        disaster_id,
        updated_disaster
    )

    if disaster is None:

        raise HTTPException(
            status_code=404,
            detail="Disaster Event not found"
        )

    return disaster

@router.delete("/{disaster_id}", response_model=DisasterEventResponse)
def delete_disaster_event(
    disaster_id: int,
    db: Session = Depends(get_db)
):

    disaster = delete_disaster(
        db,
        disaster_id
    )

    if disaster is None:

        raise HTTPException(
            status_code=404,
            detail="Disaster Event not found"
        )

    return disaster