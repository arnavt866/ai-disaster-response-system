"""Operational analytics routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.analytics.analytics_service import (
    get_allocation_reports,
    get_operations_dashboard,
)
from app.services.analytics.situation_report_service import (
    get_situation_report,
    render_situation_report_html,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def dashboard_metrics(db: Session = Depends(get_db)):
    return get_operations_dashboard(db)


@router.get("/reports")
def allocation_report_charts(db: Session = Depends(get_db)):
    return get_allocation_reports(db)


@router.get("/situation-report/{disaster_id}")
def situation_report(disaster_id: int, db: Session = Depends(get_db)):
    try:
        return get_situation_report(db, disaster_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/situation-report/{disaster_id}/html", response_class=HTMLResponse)
def situation_report_html(
    disaster_id: int,
    bare: bool = False,
    db: Session = Depends(get_db),
):
    """Downloaded HTML never includes a print toolbar.

    In-app preview has its own Print control with ``print:hidden``. The file
    download is always a clean dossier so PDF printers that ignore ``@media
    print`` cannot bake a button into the export. ``bare`` is accepted for
    compatibility and ignored.
    """
    try:
        payload = get_situation_report(db, disaster_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    html = render_situation_report_html(payload, include_print_bar=False)
    event_id = payload["disaster"].get("event_id") or "event"
    safe_event = "".join(
        ch if ch.isalnum() or ch in "-_" else "-" for ch in str(event_id)
    )
    filename = f"DRMS-situation-report-{disaster_id}-{safe_event}.html"
    return HTMLResponse(
        content=html,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
