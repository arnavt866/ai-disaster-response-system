import math

from shapely.geometry import Polygon, box

from app.config.settings import GRID_CELL_SIZE


def generate_grid(
    polygon: Polygon,
    cell_size: float = GRID_CELL_SIZE,
) -> list[Polygon]:
    """
    Divide an impact polygon into square grid cells.

    Returns only cells intersecting
    the disaster polygon.
    """

    minx, miny, maxx, maxy = polygon.bounds

    rows = math.ceil((maxy - miny) / cell_size)
    cols = math.ceil((maxx - minx) / cell_size)

    grid = []

    for row in range(rows):

        for col in range(cols):

            cell = box(

                minx + col * cell_size,

                miny + row * cell_size,

                minx + (col + 1) * cell_size,

                miny + (row + 1) * cell_size,

            )

            if cell.intersects(polygon):

                clipped = cell.intersection(polygon)

                if not clipped.is_empty:

                    grid.append(clipped)

    return grid