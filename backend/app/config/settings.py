import os
from pathlib import Path

from dotenv import load_dotenv

# ======================================================
# ENVIRONMENT VARIABLES
# ======================================================

load_dotenv()

USGS_URL = os.getenv(
    "USGS_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
)

GDACS_URL = os.getenv(
    "GDACS_URL",
    "",
)

NDMA_URL = os.getenv(
    "NDMA_URL",
    "",
)

NDMA_PORTAL_URL = os.getenv(
    "NDMA_PORTAL_URL",
    "https://sachet.ndma.gov.in/",
)

OVERPASS_URL = os.getenv(
    "OVERPASS_URL",
    "https://overpass.openstreetmap.ru/api/interpreter",
)

SENTINEL_STAC_URL = os.getenv(
    "SENTINEL_STAC_URL",
    "https://earth-search.aws.element84.com/v1",
)

SENTINEL_STAC_COLLECTION = os.getenv(
    "SENTINEL_STAC_COLLECTION",
    "sentinel-2-l2a",
)

HTTP_CONNECT_TIMEOUT = float(os.getenv("HTTP_CONNECT_TIMEOUT", "10"))
HTTP_READ_TIMEOUT = float(os.getenv("HTTP_READ_TIMEOUT", "20"))

DATABASE_URL = os.getenv("DATABASE_URL")

# ======================================================
# PROJECT PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

MODEL_DIR = PROJECT_ROOT / "models"

DATASET_DIR = PROJECT_ROOT / "datasets"

# ======================================================
# DATA FILES
# ======================================================

OSM_FILE = DATA_DIR / "osm" / "india-latest.osm.pbf"

POPULATION_RASTER = DATA_DIR / "population" / "india_population.tif"

NWIC_DISTRICTS_GEOJSON = DATA_DIR / "district_nwic.GeoJSON"

TARGET_DISTRICTS_GEOJSON = DATA_DIR / "district_target_states.geojson"

HISTORICAL_XML_PATHS = {
    "Odisha": DATA_DIR / "orissa" / "DI_export_019" / "DI_export_019.xml",
    "Tamil Nadu": DATA_DIR / "tamil_nadu" / "DI_export_033" / "DI_export_033.xml",
    "Uttarakhand": DATA_DIR / "uttarakhand" / "DI_export_005" / "DI_export_005.xml",
}

REPORTS_DIR = DATASET_DIR / "reports"

# ======================================================
# IMPORT SETTINGS
# ======================================================

BUILDING_IMPORT_BATCH_SIZE = 1000

# ======================================================
# GRID SETTINGS
# ======================================================

GRID_CELL_SIZE = 0.02

KM_PER_DEGREE = 111.32

# ======================================================
# DEFAULT DISASTER RADII (Kilometres)
# ======================================================

DEFAULT_RADIUS = 30

DEFAULT_EARTHQUAKE_RADIUS = 20

DEFAULT_FLOOD_RADIUS = 40

DEFAULT_CYCLONE_RADIUS = 100