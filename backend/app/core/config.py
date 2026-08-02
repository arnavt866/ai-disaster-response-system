import os
from dotenv import load_dotenv

load_dotenv()

USGS_URL = os.getenv(
    "USGS_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
)

GDACS_URL = os.getenv(
    "GDACS_URL",
    ""
)

NDMA_URL = os.getenv(
    "NDMA_URL",
    ""
)