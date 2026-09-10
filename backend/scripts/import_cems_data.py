"""Import Copernicus EMS EMSR357 Cyclone Fani data into SatelliteAssessment table."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import geopandas as gpd
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement

from app.database.connection import SessionLocal
from app.models.satellite_assessment import SatelliteAssessment
from app.config.settings import PROJECT_ROOT

CEMS_DATA_PATH = PROJECT_ROOT / "data" / "satellite" / "cems" / "emsr357_fani"

def import_cems_package(package_path, product_type, pattern_suffix):
    """Import observedEventA shapefiles from a CEMS package."""
    db = SessionLocal()
    
    try:
        # Import observedEventA polygons (damage assessment)
        pattern = f"*observedEventA*{pattern_suffix}.shp"
        event_shp = list(package_path.glob(pattern))
        
        if not event_shp:
            print(f"Skipping {package_path.name}: no observedEventA shapefile found matching {pattern}")
            return 0
        
        event_shp = event_shp[0]
        print(f"Processing: {event_shp.name}")
        
        gdf = gpd.read_file(event_shp)
        
        # Convert to WGS84 if needed
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        imported = 0
        for _, row in gdf.iterrows():
            # Get classification from various possible field names
            classification = (row.get("classificati") or row.get("CLASSIFICAT") or 
                            row.get("classifica") or row.get("CLASSIFICA") or "Unknown")
            
            assessment = SatelliteAssessment(
                activation_code="EMSR357",
                event_name="Cyclone Fani 2019",
                event_date="2019-05-03",
                product_type=product_type,
                source_url="https://emergency.copernicus.eu/mapping/list-of-components/EMSR357",
                geometry=WKTElement(row.geometry.wkt, srid=4326),
                classification=str(classification),
                area_m2=float(row.geometry.area),
                source_license="Copernicus Emergency Management Service - free for use",
            )
            db.add(assessment)
            imported += 1
        
        db.commit()
        print(f"Imported {imported} features from {package_path.name}")
        return imported
        
    except Exception as e:
        db.rollback()
        print(f"Error importing {package_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        db.close()

def main():
    print("Starting CEMS EMSR357 Cyclone Fani data import...")
    
    delineation_path = CEMS_DATA_PATH / "delineation" / "EMSR357_AOI01_DEL_PRODUCT_r1_VECTORS_v4_vector"
    grading_path = CEMS_DATA_PATH / "grading" / "EMSR357_AOI05_GRA_PRODUCT_r1_VECTORS_v1_vector"
    
    total = 0
    total += import_cems_package(delineation_path, "delineation", "r1_v4")
    total += import_cems_package(grading_path, "grading", "r1_v1")
    
    print(f"Total features imported: {total}")
    
    # Verify import
    db = SessionLocal()
    count = db.query(SatelliteAssessment).count()
    print(f"Total SatelliteAssessment rows: {count}")
    db.close()

if __name__ == "__main__":
    main()
