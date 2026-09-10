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

SACHET_RSS_URL = os.getenv(
    "SACHET_RSS_URL",
    "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml",
)

SACHET_CAP_URL = os.getenv(
    "SACHET_CAP_URL",
    "https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile",
)

SACHET_POLYGON_URL = os.getenv(
    "SACHET_POLYGON_URL",
    "https://sachet.ndma.gov.in/cap_public_website/FetchPolygonXMLFile",
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

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-only-change-me-before-production",
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480")
)
DEFAULT_COMMANDER_USERNAME = os.getenv("DEFAULT_COMMANDER_USERNAME", "commander")
DEFAULT_COMMANDER_PASSWORD = os.getenv("DEFAULT_COMMANDER_PASSWORD", "commander")

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

POPULATION_DIR = DATA_DIR / "population"

# WorldPop R2025A age/sex (1km). Filename pattern from hub.worldpop.org:
#   {iso}_{gender}_{age}_{year}_{type}_{resolution}_{release}_{version}.tif
# Example: ind_t_00_2025_CN_1km_R2025A_v1.tif  (both sexes, ages 0–12 months)
# Prefer both-sexes (t) files; code also accepts paired m+f files for the same band.
# Override any of these via env, or pass explicit comma-separated raster lists.
WORLDPOP_AGESEX_ISO = os.getenv("WORLDPOP_AGESEX_ISO", "ind")
WORLDPOP_AGESEX_YEAR = os.getenv("WORLDPOP_AGESEX_YEAR", "2025")
WORLDPOP_AGESEX_TYPE = os.getenv("WORLDPOP_AGESEX_TYPE", "CN")
WORLDPOP_AGESEX_RESOLUTION = os.getenv("WORLDPOP_AGESEX_RESOLUTION", "1km")
WORLDPOP_AGESEX_RELEASE = os.getenv("WORLDPOP_AGESEX_RELEASE", "R2025A")
WORLDPOP_AGESEX_VERSION = os.getenv("WORLDPOP_AGESEX_VERSION", "v1")

# 00=0–1, 01=1–4, 05=5–9, 10=10–14  →  population 0–14
WORLDPOP_CHILD_AGE_GROUPS: tuple[str, ...] = ("00", "01", "05", "10")
# 60=60–64 … 90=90+  →  population 60+
WORLDPOP_ELDERLY_AGE_GROUPS: tuple[str, ...] = (
    "60",
    "65",
    "70",
    "75",
    "80",
    "85",
    "90",
)

# Optional explicit local paths (comma-separated). When set, the glob pattern is ignored.
WORLDPOP_CHILD_RASTERS_ENV = os.getenv("WORLDPOP_CHILD_RASTERS", "")
WORLDPOP_ELDERLY_RASTERS_ENV = os.getenv("WORLDPOP_ELDERLY_RASTERS", "")


def worldpop_agesex_filename(age_group: str, gender: str = "t") -> str:
    return (
        f"{WORLDPOP_AGESEX_ISO}_{gender}_{age_group}_{WORLDPOP_AGESEX_YEAR}_"
        f"{WORLDPOP_AGESEX_TYPE}_{WORLDPOP_AGESEX_RESOLUTION}_"
        f"{WORLDPOP_AGESEX_RELEASE}_{WORLDPOP_AGESEX_VERSION}.tif"
    )


def worldpop_agesex_path(age_group: str, gender: str = "t") -> Path:
    return POPULATION_DIR / worldpop_agesex_filename(age_group, gender)

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