from pathlib import Path

from rasterstats import zonal_stats

from app.config.settings import (
    POPULATION_RASTER,
    WORLDPOP_CHILD_AGE_GROUPS,
    WORLDPOP_CHILD_RASTERS_ENV,
    WORLDPOP_ELDERLY_AGE_GROUPS,
    WORLDPOP_ELDERLY_RASTERS_ENV,
    worldpop_agesex_path,
)

POPULATION_NODATA = -99999
WORLDPOP_AGE_SEX_SOURCE = "worldpop_age_sex_r2025a"


def _parse_raster_list(raw: str) -> list[Path]:
    return [Path(item.strip()) for item in raw.split(",") if item.strip()]


def _band_raster_paths(age_group: str) -> list[Path]:
    """Resolve one age-band raster: both-sexes file, else male+female pair."""
    both = worldpop_agesex_path(age_group, "t")
    if both.exists():
        return [both]
    male = worldpop_agesex_path(age_group, "m")
    female = worldpop_agesex_path(age_group, "f")
    if male.exists() and female.exists():
        return [male, female]
    return []


def resolve_child_raster_paths() -> list[Path]:
    if WORLDPOP_CHILD_RASTERS_ENV:
        return _parse_raster_list(WORLDPOP_CHILD_RASTERS_ENV)
    paths: list[Path] = []
    for age_group in WORLDPOP_CHILD_AGE_GROUPS:
        band = _band_raster_paths(age_group)
        if not band:
            return []
        paths.extend(band)
    return paths


def resolve_elderly_raster_paths() -> list[Path]:
    if WORLDPOP_ELDERLY_RASTERS_ENV:
        return _parse_raster_list(WORLDPOP_ELDERLY_RASTERS_ENV)
    paths: list[Path] = []
    for age_group in WORLDPOP_ELDERLY_AGE_GROUPS:
        band = _band_raster_paths(age_group)
        if not band:
            return []
        paths.extend(band)
    return paths


def age_sex_rasters_available(
    child_rasters: list[Path] | None = None,
    elderly_rasters: list[Path] | None = None,
) -> bool:
    child_paths = child_rasters if child_rasters is not None else resolve_child_raster_paths()
    elderly_paths = (
        elderly_rasters if elderly_rasters is not None else resolve_elderly_raster_paths()
    )
    if not child_paths or not elderly_paths:
        return False
    return all(path.exists() for path in (*child_paths, *elderly_paths))


def _zonal_sum(polygon_geojson: dict, raster_path: Path) -> float:
    stats = zonal_stats(
        polygon_geojson,
        str(raster_path),
        stats=["sum"],
        nodata=POPULATION_NODATA,
    )
    if not stats:
        return 0.0
    return float(stats[0].get("sum") or 0.0)


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

    population = _zonal_sum(polygon_geojson, POPULATION_RASTER)

    return {
        "estimated_population": int(population)
    }


def estimate_age_sex_population(
    polygon_geojson: dict,
    *,
    child_rasters: list[Path] | None = None,
    elderly_rasters: list[Path] | None = None,
    total_raster: Path | None = None,
) -> dict:
    """Zonal sums for ages 0–14 and 60+, plus shares of total WorldPop count.

    Returns data_available=False when any required raster is missing. Never raises
    for missing files — callers fall back to the neutral vulnerability factor.
    """
    child_paths = child_rasters if child_rasters is not None else resolve_child_raster_paths()
    elderly_paths = (
        elderly_rasters if elderly_rasters is not None else resolve_elderly_raster_paths()
    )
    total_path = total_raster if total_raster is not None else POPULATION_RASTER

    if not age_sex_rasters_available(child_paths, elderly_paths) or not total_path.exists():
        return {
            "population_0_14": 0.0,
            "population_60_plus": 0.0,
            "elderly_share": None,
            "child_share": None,
            "total_population": 0.0,
            "data_available": False,
            "source": "unavailable",
        }

    population_0_14 = sum(_zonal_sum(polygon_geojson, path) for path in child_paths)
    population_60_plus = sum(_zonal_sum(polygon_geojson, path) for path in elderly_paths)
    total_population = _zonal_sum(polygon_geojson, total_path)

    if total_population <= 0:
        return {
            "population_0_14": population_0_14,
            "population_60_plus": population_60_plus,
            "elderly_share": None,
            "child_share": None,
            "total_population": total_population,
            "data_available": False,
            "source": "unavailable",
        }

    return {
        "population_0_14": population_0_14,
        "population_60_plus": population_60_plus,
        "elderly_share": population_60_plus / total_population,
        "child_share": population_0_14 / total_population,
        "total_population": total_population,
        "data_available": True,
        "source": WORLDPOP_AGE_SEX_SOURCE,
    }
