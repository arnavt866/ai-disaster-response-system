"""Operational analytics routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.analytics.analytics_service import get_operations_dashboard

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def dashboard_metrics(db: Session = Depends(get_db)):
    return get_operations_dashboard(db)
