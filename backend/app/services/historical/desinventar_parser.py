"""Reusable DESINVENTAR (NWDP) XML parser for historical disaster records."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from app.core.logger import logger

# Fields captured from each <fichas><TR> disaster record.
FICHA_RECORD_FIELDS: tuple[str, ...] = (
    "serial",
    "level0",
    "level1",
    "level2",
    "name0",
    "name1",
    "name2",
    "evento",
    "lugar",
    "fechano",
    "fechames",
    "fechadia",
    "muertos",
    "heridos",
    "desaparece",
    "afectados",
    "vivdest",
    "vivafec",
    "otros",
    "fuentes",
    "valorloc",
    "valorus",
    "fechapor",
    "fechafec",
    "hay_muertos",
    "hay_heridos",
    "hay_deasparece",
    "hay_afectados",
    "hay_vivdest",
    "hay_vivafec",
    "hay_otros",
    "socorro",
    "salud",
    "educacion",
    "agropecuario",
    "industrias",
    "acueducto",
    "alcantarillado",
    "energia",
    "comunicaciones",
    "causa",
    "descausa",
    "transporte",
    "magnitud2",
    "nhospitales",
    "nescuelas",
    "nhectareas",
    "cabezas",
    "kmvias",
    "duracion",
    "damnificados",
    "evacuados",
    "hay_damnificados",
    "hay_evacuados",
    "hay_reubicados",
    "reubicados",
    "latitude",
    "longitude",
    "glide",
    "uu_id",
    "approved",
    "di_comments",
)


@dataclass
class XmlSchemaInspection:
    source_file: str
    source_state: str
    top_level_sections: list[str] = field(default_factory=list)
    ficha_record_count: int = 0
    observed_fields: list[str] = field(default_factory=list)
    sample_record: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_state": self.source_state,
            "top_level_sections": self.top_level_sections,
            "ficha_record_count": self.ficha_record_count,
            "observed_fields": self.observed_fields,
            "sample_record": self.sample_record,
        }


@dataclass
class RawDisasterRecord:
    source_file: str
    source_state: str
    fields: dict[str, str]

    def to_dict(self) -> dict[str, str]:
        return {
            "source_file": self.source_file,
            "source_state": self.source_state,
            **self.fields,
        }


def _child_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _is_ficha_record(element: ET.Element) -> bool:
    return element.tag == "TR" and element.find("evento") is not None


def inspect_desinventar_xml(
    path: Path,
    source_state: str,
) -> XmlSchemaInspection:
    """Inspect a DESINVENTAR XML file and return schema metadata."""
    inspection = XmlSchemaInspection(
        source_file=str(path),
        source_state=source_state,
    )
    observed: set[str] = set()
    in_fichas = False
    current_record: dict[str, str] = {}

    for event, element in ET.iterparse(path, events=("start", "end")):
        if event == "start" and element.tag not in {"TR", "DESINVENTAR"}:
            if element.tag not in inspection.top_level_sections:
                inspection.top_level_sections.append(element.tag)
            if element.tag == "fichas":
                in_fichas = True

        if event == "end":
            if in_fichas:
                if element.tag not in {"TR", "fichas"}:
                    current_record[element.tag] = (element.text or "").strip()
                    observed.add(element.tag)

                if element.tag == "TR" and "evento" in current_record:
                    inspection.ficha_record_count += 1
                    if not inspection.sample_record:
                        inspection.sample_record = dict(current_record)
                    current_record = {}

            if element.tag == "fichas":
                in_fichas = False

            element.clear()

    inspection.observed_fields = sorted(observed)
    return inspection


def parse_desinventar_xml(
    path: Path,
    source_state: str,
) -> Iterator[RawDisasterRecord]:
    """
    Stream-parse disaster records from the <fichas> section of a DESINVENTAR XML.

    Yields one RawDisasterRecord per <TR> row that contains an <evento> field.

    Child field values are collected on each child </tag> end event because
    iterparse clears children before the parent <TR> end event fires.
    """
    if not path.exists():
        raise FileNotFoundError(f"Historical XML not found: {path}")

    logger.info("Parsing DESINVENTAR XML: %s", path)
    in_fichas = False
    current_record: dict[str, str] = {}
    count = 0

    for event, element in ET.iterparse(path, events=("start", "end")):
        if event == "start" and element.tag == "fichas":
            in_fichas = True

        if event == "end":
            if in_fichas:
                if element.tag not in {"TR", "fichas"}:
                    current_record[element.tag] = (element.text or "").strip()

                if element.tag == "TR":
                    if "evento" in current_record:
                        count += 1
                        yield RawDisasterRecord(
                            source_file=str(path),
                            source_state=source_state,
                            fields=dict(current_record),
                        )
                    current_record = {}

            if element.tag == "fichas":
                in_fichas = False

            element.clear()

    logger.info("Parsed %d records from %s", count, path.name)


def parse_all_historical_xml(
    xml_paths: dict[str, Path],
) -> tuple[list[RawDisasterRecord], list[XmlSchemaInspection]]:
    """Parse all configured state XML files."""
    records: list[RawDisasterRecord] = []
    inspections: list[XmlSchemaInspection] = []

    for source_state, path in xml_paths.items():
        inspection = inspect_desinventar_xml(path, source_state)
        inspections.append(inspection)
        records.extend(parse_desinventar_xml(path, source_state))

    return records, inspections
