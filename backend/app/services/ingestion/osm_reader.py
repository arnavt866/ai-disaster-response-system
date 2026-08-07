from typing import Callable

import osmium

from app.config.settings import (
    BUILDING_IMPORT_BATCH_SIZE,
    OSM_FILE,
)
from app.core.logger import logger

if not OSM_FILE.exists():
    raise FileNotFoundError(
        f"OSM file not found: {OSM_FILE}"
    )


class BuildingStreamHandler(osmium.SimpleHandler):
    """
    Streams buildings from the OSM file.

    It never stores the whole country in RAM.

    Every BATCH_SIZE buildings,
    callback(buildings)
    is called.
    """

    def __init__(
        self,
        callback: Callable,
        batch_size: int = BUILDING_IMPORT_BATCH_SIZE,
    ):

        super().__init__()

        self.callback = callback

        self.batch_size = batch_size

        self.batch: list[dict] = []

        self.total: int = 0

    def way(self, way) -> None:

        if "building" not in way.tags:
            return

        if len(way.nodes) == 0:
            return

        try:

            node = way.nodes[0]

            self.batch.append({

                "osm_id": int(way.id),

                "latitude": float(node.lat),

                "longitude": float(node.lon),

            })

            self.total += 1
            if self.total % 100000 == 0:
                logger.info(f"Read {self.total:,} buildings...")
            if len(self.batch) >= self.batch_size:

                self.callback(self.batch)

                self.batch.clear()

        except Exception as e:

            logger.warning(

                f"Skipping building "

                f"{way.id}: {e}"

            )

            return

    def finish(self) -> None:

        if self.batch:

            self.callback(self.batch)

            self.batch.clear()