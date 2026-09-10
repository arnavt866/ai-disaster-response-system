from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# API routers
from app.api.allocation_routes import router as allocation_router
from app.api.analytics_routes import router as analytics_router
from app.api.auth_dependencies import require_commander
from app.api.auth_routes import router as auth_router
from app.api.field_team_routes import router as field_team_router
from app.api.mission_routes import router as mission_router
from app.api.building_routes import router as building_router
from app.api.disaster_routes import router as disaster_router
from app.api.gdacs_routes import router as gdacs_router
from app.api.grid_routes import router as grid_router
from app.api.impact_routes import router as impact_router
from app.api.inventory_routes import router as inventory_router
from app.api.ndma_routes import router as ndma_router
from app.api.relief_routes import router as relief_router
from app.api.satellite_routes import router as satellite_router
from app.api.system_routes import router as system_router
from app.api.prediction_routes import compat_router as prediction_compat_router
from app.api.prediction_routes import router as prediction_router
from app.api.usgs_routes import router as usgs_router
from app.api.zone_routes import router as zone_router
from app.database.connection import SessionLocal
from app.services.auth_service import ensure_default_commander

protected = [Depends(require_commander)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        ensure_default_commander(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="AI Disaster Response Management System",
    version="1.0.0",
    description=(
        "Backend API for AI-based disaster response, "
        "resource allocation, and relief coordination."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(auth_router)

# Protected API routes
app.include_router(allocation_router, dependencies=protected)
app.include_router(analytics_router, dependencies=protected)
app.include_router(field_team_router, dependencies=protected)
app.include_router(mission_router, dependencies=protected)
app.include_router(building_router, dependencies=protected)
app.include_router(disaster_router, dependencies=protected)
app.include_router(gdacs_router, dependencies=protected)
app.include_router(grid_router, dependencies=protected)
app.include_router(impact_router, dependencies=protected)
app.include_router(inventory_router, dependencies=protected)
app.include_router(ndma_router, dependencies=protected)
app.include_router(relief_router, dependencies=protected)
app.include_router(satellite_router, dependencies=protected)
app.include_router(system_router, dependencies=protected)
app.include_router(prediction_router, dependencies=protected)
app.include_router(prediction_compat_router, dependencies=protected)
app.include_router(usgs_router, dependencies=protected)
app.include_router(zone_router, dependencies=protected)


@app.get("/", tags=["Health"])
def home():
    """
    Health check endpoint.
    """

    return {
        "message": "AI Disaster Response Management System API is running."
    }
