"""Build Chennai 2015 flood scenario pack from KML files."""

import geopandas as gpd
import pandas as pd
from pathlib import Path

SCENARIO_PATH = Path(__file__).parent.parent / "data" / "scenarios" / "chennai_floods_2015"
OUTPUT_PATH = SCENARIO_PATH / "district_metrics.csv"

def parse_kml_to_metrics(kml_path, source_document, data_quality_note):
    """Parse KML file and extract basic metrics."""
    try:
        gdf = gpd.read_file(kml_path)
        
        metrics = []
        for _, row in gdf.iterrows():
            # Extract whatever fields are available
            metric = {
                "taluk": row.get("Name", row.get("name", "Unknown")),
                "affected_population": row.get("Population", row.get("population", None)),
                "houses_damaged": row.get("Houses_Damaged", row.get("houses_damaged", None)),
                "houses_destroyed": row.get("Houses_Destroyed", row.get("houses_destroyed", None)),
                "inundation_area_km2": row.get("Area_KM2", row.get("area_km2", None)),
                "severity_level": row.get("Severity", row.get("severity", "Moderate")),
                "geometry_type": row.geometry.geom_type if hasattr(row.geometry, 'geom_type') else "Unknown",
                "source_document": source_document,
                "data_quality_note": data_quality_note,
                "scenario": "Chennai Floods 2015",
                "year": 2015
            }
            metrics.append(metric)
        
        return metrics
    except Exception as e:
        print(f"Error parsing {kml_path}: {e}")
        return []

def main():
    print("Building Chennai 2015 scenario pack...")
    
    gis_path = SCENARIO_PATH / "gis"
    
    all_metrics = []
    
    # Parse NRSC inundation zone
    nrsc_kml = gis_path / "inundation_zone_nrsc.kml"
    if nrsc_kml.exists():
        print(f"Processing {nrsc_kml.name}...")
        metrics = parse_kml_to_metrics(
            nrsc_kml,
            "NRSC Chennai Flood Inundation Zone 2015",
            "Satellite-derived inundation mapping, limited validation"
        )
        all_metrics.extend(metrics)
    
    # Parse GCC hotspots
    gcc_kml = gis_path / "gcc_flood_hotspots.kml"
    if gcc_kml.exists():
        print(f"Processing {gcc_kml.name}...")
        metrics = parse_kml_to_metrics(
            gcc_kml,
            "GCC Flood Hotspots 2015",
            "Greater Chennai Corporation field reports, limited geographic coverage"
        )
        all_metrics.extend(metrics)
    
    # Parse Tiruvallur hotspots
    tiruvallur_kml = gis_path / "tiruvallur_flood_hotspots.kml"
    if tiruvallur_kml.exists():
        print(f"Processing {tiruvallur_kml.name}...")
        metrics = parse_kml_to_metrics(
            tiruvallur_kml,
            "Tiruvallur Flood Hotspots 2015",
            "District-level flood impact reports, limited validation"
        )
        all_metrics.extend(metrics)
    
    # Create DataFrame and aggregate by district
    if all_metrics:
        df = pd.DataFrame(all_metrics)
        
        # Aggregate to district level
        district_agg = df.groupby('district').agg({
            'affected_population': 'sum',
            'houses_damaged': 'sum', 
            'houses_destroyed': 'sum',
            'inundation_area_km2': 'sum',
            'severity_level': lambda x: x.mode()[0] if not x.mode().empty else 'Moderate',
            'source_document': lambda x: '; '.join(set(x)),
            'data_quality_note': lambda x: '; '.join(set(x)),
            'scenario': 'first',
            'year': 'first'
        }).reset_index()
        
        # Remove geometry_type if it exists
        if 'geometry_type' in district_agg.columns:
            district_agg = district_agg.drop(columns=['geometry_type'])
        
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        district_agg.to_csv(OUTPUT_PATH, index=False)
        print(f"Saved {len(district_agg)} district records to {OUTPUT_PATH}")
        print(f"Districts: {district_agg['district'].tolist()}")
    else:
        print("No metrics extracted from KML files")

if __name__ == "__main__":
    main()
