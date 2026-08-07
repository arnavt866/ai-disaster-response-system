

from rasterstats import zonal_stats

from app.config.settings import POPULATION_RASTER


def estimate_population(
    polygon_geojson: dict,
) -> dict:
    """
    Estimate population inside a polygon using WorldPop raster.
    """

    if not POPULATION_RASTER.exists():
        return {
            "estimated_population": 0,
            "message": "Population raster not found."
        }

    stats = zonal_stats(
        polygon_geojson,
        str(POPULATION_RASTER),
        stats=["sum"],
        nodata=-99999,
    )

    if not stats:
        return {
            "estimated_population": 0
        }

    population = stats[0].get("sum") or 0

    return {
        "estimated_population": int(population)
    }