"""Import EMSR357 (Cyclone Fani) observedEventA polygons into PostGIS.

Keeps original zip files. Loads delineation flood-extent polygons and grading
observed-event polygons. Reprojects to EPSG:4326 if needed.
"""

from __future__ import annotations

import zipfile
from datetime import date, datetime
from pathlib import Path

import geopandas as gpd
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import text

from app.config.settings import DATA_DIR
from app.database.connection import SessionLocal
from app.models.satellite_assessment import SatelliteAssessment

CEMS_ROOT = DATA_DIR / "satellite" / "cems" / "emsr357_fani"
ACTIVATION = "EMSR357"
EVENT_NAME = "Cyclone Fani"
EVENT_DATE = date(2019, 5, 3)
SOURCE_URL = "https://emergency.copernicus.eu/mapping/list-of-components/EMSR357"
SOURCE_LICENSE = (
    "© European Union, Copernicus Emergency Management Service (EMSR357), 2019. "
    "Rapid Mapping vectors. Not AI-detected damage."
)
SKIP_DAMAGE_GRA = {"", "None", "Not Applicable"}


def extract_zips(folder: Path) -> None:
    for zip_path in folder.glob("*.zip"):
        dest = folder / zip_path.stem
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(dest)


def _as_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    geom = geom.buffer(0)
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "GeometryCollection":
        polys = [part for part in geom.geoms if isinstance(part, Polygon) and not part.is_empty]
        if polys:
            return MultiPolygon(polys)
    return None


def _classification(properties: dict) -> str | None:
    damage = str(properties.get("damage_gra") or "").strip()
    if damage and damage not in SKIP_DAMAGE_GRA and damage != "Not Analysed":
        return damage
    notation = str(properties.get("notation") or "").strip()
    if notation and notation not in SKIP_DAMAGE_GRA:
        return notation
    if damage:
        return damage
    obj_desc = str(properties.get("obj_desc") or "").strip()
    return obj_desc or None


def load_observed_event_polygons(product_type: str) -> gpd.GeoDataFrame:
    folder = CEMS_ROOT / product_type
    extract_zips(folder)
    shp = next(folder.rglob("*observedEventA*.shp"))
    frame = gpd.read_file(shp)
    if frame.crs is None:
        frame = frame.set_crs(epsg=4326)
    elif str(frame.crs) != "EPSG:4326":
        frame = frame.to_crs(epsg=4326)
    return frame


def import_emsr357(db) -> dict[str, int]:
    db.query(SatelliteAssessment).filter(
        SatelliteAssessment.activation_code == ACTIVATION
    ).delete()
    counts = {"delineation": 0, "grading": 0}
    now = datetime.utcnow()
    for product_type in ("delineation", "grading"):
        frame = load_observed_event_polygons(product_type)
        for _, row in frame.iterrows():
            geom = _as_multipolygon(row.geometry)
            if geom is None:
                continue
            props = {k: row[k] for k in frame.columns if k != "geometry"}
            db.add(
                SatelliteAssessment(
                    activation_code=ACTIVATION,
                    event_name=EVENT_NAME,
                    event_date=EVENT_DATE,
                    product_type=product_type,
                    source_url=SOURCE_URL,
                    geometry=from_shape(geom, srid=4326),
                    classification=_classification(props),
                    source_license=SOURCE_LICENSE,
                    imported_at=now,
                )
            )
            counts[product_type] += 1
    db.commit()
    db.execute(
        text(
            """
            UPDATE satellite_assessments
            SET area_m2 = ST_Area(geometry::geography)
            WHERE activation_code = :code
            """
        ),
        {"code": ACTIVATION},
    )
    db.commit()
    return counts


def main() -> None:
    db = SessionLocal()
    try:
        counts = import_emsr357(db)
        total = db.query(SatelliteAssessment).filter(
            SatelliteAssessment.activation_code == ACTIVATION
        ).count()
        print(f"imported {counts} total_rows={total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
