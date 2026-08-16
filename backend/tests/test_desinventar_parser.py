"""Tests for DESINVENTAR XML parser."""

from pathlib import Path

import pytest

from app.config.settings import HISTORICAL_XML_PATHS
from app.services.historical.desinventar_parser import (
    inspect_desinventar_xml,
    parse_desinventar_xml,
)


@pytest.fixture
def orissa_xml() -> Path:
    return HISTORICAL_XML_PATHS["Odisha"]


def test_orissa_xml_exists(orissa_xml: Path):
    assert orissa_xml.exists()


def test_inspect_orissa_schema(orissa_xml: Path):
    inspection = inspect_desinventar_xml(orissa_xml, "Odisha")
    assert inspection.ficha_record_count > 0
    assert "evento" in inspection.observed_fields
    assert "name1" in inspection.observed_fields
    assert "afectados" in inspection.observed_fields


def test_parse_orissa_sample_records(orissa_xml: Path):
    records = list(parse_desinventar_xml(orissa_xml, "Odisha"))
    assert len(records) > 1000
    sample = records[0]
    assert sample.source_state == "Odisha"
    assert sample.fields.get("evento")
    assert sample.fields.get("name1")


def test_no_resource_demand_fields_in_xml(orissa_xml: Path):
    inspection = inspect_desinventar_xml(orissa_xml, "Odisha")
    forbidden = {"food", "water", "medical", "shelter", "packet", "kit"}
    observed = {f.lower() for f in inspection.observed_fields}
    assert not (observed & forbidden), (
        f"Unexpected resource-demand fields found: {observed & forbidden}"
    )
