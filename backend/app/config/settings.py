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