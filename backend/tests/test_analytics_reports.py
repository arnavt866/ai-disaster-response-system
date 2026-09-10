"""Allocation analytics charts and disaster situation reports."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.allocation_record import AllocationRecord
from app.models.disaster_event import DisasterEvent
from app.models.disaster_zone import DisasterZone
from app.models.field_team import FieldTeam
from app.models.mission import Mission
from app.models.relief_center import ReliefCenter

client = TestClient(app)


def _seed_report_data(db):
    depot = ReliefCenter(
        name="Chennai Relief Camp",
        address="Chennai",
        latitude=13.08,
        longitude=80.27,
        capacity=1000,
        available_capacity=800,
        status="Active",
    )
    zone = DisasterZone(
        zone_name="EQ-202608071200-Zone-1",
        disaster_type="EQ",
        severity="Critical",
        latitude=13.10,
        longitude=80.28,
        affected_population=12000,
        status="Active",
        operational_priority="Critical",
    )
    disaster = DisasterEvent(
        event_id="EQ-TEST-SITREP-1",
        title="Earthquake in Chennai",
        disaster_type="EQ",
        magnitude=6.2,
        latitude=13.0827,
        longitude=80.2707,
        location="Chennai, Tamil Nadu",
        severity="High",
        status="Active",
        source="test",
        event_time=datetime.utcnow(),
    )
    db.add_all([depot, zone, disaster])
    db.flush()

    earlier = datetime.utcnow() - timedelta(hours=6)
    later = datetime.utcnow() - timedelta(hours=1)
    db.add_all(
        [
            AllocationRecord(
                run_id="run-a",
                zone_id=zone.id,
                relief_center_id=depot.id,
                resource_category="food",
                demanded=100,
                allocated=40,
                unmet=60,
                created_at=earlier,
            ),
            AllocationRecord(
                run_id="run-b",
                zone_id=zone.id,
                relief_center_id=depot.id,
                resource_category="food",
                demanded=100,
                allocated=80,
                unmet=20,
                created_at=later,
            ),
            AllocationRecord(
                run_id="run-b",
                zone_id=zone.id,
                relief_center_id=depot.id,
                resource_category="water",
                demanded=200,
                allocated=200,
                unmet=0,
                created_at=later,
            ),
        ]
    )
    team = FieldTeam(
        team_name="Alpha Response",
        status="Assigned",
        vehicle_type="Truck",
        vehicle_capacity=4000,
        personnel_count=6,
        base_latitude=13.08,
        base_longitude=80.27,
    )
    db.add(team)
    db.flush()
    db.add(
        Mission(
            mission_code="MSN-SITREP-TEST",
            zone_id=zone.id,
            field_team_id=team.id,
            relief_center_id=depot.id,
            priority="Critical",
            status="Dispatched",
            route_distance_km=12.5,
            route_eta_hours=0.4,
            route_status="open",
            resources_payload='{"food": 80}',
        )
    )
    db.flush()
    return disaster, zone, depot


def test_allocation_reports_endpoint(db_session):
    _seed_report_data(db_session)
    response = client.get("/analytics/reports")
    assert response.status_code == 200
    body = response.json()
    assert body["data_source"] == "database"
    by_run = {row["run_id"]: row for row in body["coverage_trend"]}
    assert by_run["run-a"]["allocated"] == 40
    assert by_run["run-a"]["unmet"] == 60
    assert by_run["run-a"]["unmet_ratio"] == 0.6
    assert by_run["run-b"]["allocated"] == 280
    assert by_run["run-b"]["unmet"] == 20
    assert any(row["category"] == "food" for row in body["category_breakdown"])
    assert any(row["zone_name"] == "EQ-202608071200-Zone-1" for row in body["critical_zones"])


def test_allocation_reports_excludes_inactive_zones(db_session):
    active = DisasterZone(
        zone_name="Active Gap Zone",
        disaster_type="EQ",
        severity="High",
        latitude=13.11,
        longitude=80.29,
        affected_population=5000,
        status="Active",
        operational_priority="High",
    )
    inactive = DisasterZone(
        zone_name="M3 Test Zone",
        disaster_type="EQ",
        severity="Critical",
        latitude=13.12,
        longitude=80.30,
        affected_population=100,
        status="Inactive",
        operational_priority="Critical",
    )
    depot = ReliefCenter(
        name="Chennai Relief Camp",
        address="Chennai",
        latitude=13.08,
        longitude=80.27,
        capacity=1000,
        available_capacity=800,
        status="Active",
    )
    db_session.add_all([active, inactive, depot])
    db_session.flush()
    db_session.add_all(
        [
            AllocationRecord(
                run_id="run-active",
                zone_id=active.id,
                relief_center_id=depot.id,
                resource_category="food",
                demanded=200,
                allocated=50,
                unmet=150,
            ),
            AllocationRecord(
                run_id="run-inactive",
                zone_id=inactive.id,
                relief_center_id=depot.id,
                resource_category="food",
                demanded=999_999,
                allocated=0,
                unmet=999_999,
            ),
        ]
    )
    db_session.flush()

    response = client.get("/analytics/reports")
    assert response.status_code == 200
    body = response.json()
    zone_names = [row["zone_name"] for row in body["critical_zones"]]
    assert "M3 Test Zone" not in zone_names
    gap = next(row for row in body["critical_zones"] if row["zone_name"] == "Active Gap Zone")
    assert gap["unmet"] == 150
    assert gap["status"] == "Active"


def test_reports_drop_runs_supplied_by_quarantined_depots(db_session):
    """A quarantined pytest depot supplying an Active zone must not fabricate a gap."""
    zone = DisasterZone(
        zone_name="EQ-202608071200-Zone-733",
        disaster_type="EQ",
        severity="High",
        latitude=13.14,
        longitude=80.31,
        affected_population=8000,
        status="Active",
        operational_priority="Moderate",
    )
    live_depot = ReliefCenter(
        name="Bhubaneswar Depot",
        address="Bhubaneswar",
        latitude=20.29,
        longitude=85.82,
        capacity=5000,
        available_capacity=4000,
        status="Active",
    )
    fixture_depot = ReliefCenter(
        name="M3 Depot ece47c06",
        address="test",
        latitude=13.15,
        longitude=80.32,
        capacity=10000,
        available_capacity=10000,
        status="Inactive",
    )
    db_session.add_all([zone, live_depot, fixture_depot])
    db_session.flush()

    # One run fully served by the live depot, one run mostly served by the
    # quarantined fixture depot. Same zone, same category, same demand.
    db_session.add_all(
        [
            AllocationRecord(
                run_id="run-clean",
                zone_id=zone.id,
                relief_center_id=live_depot.id,
                resource_category="food",
                demanded=1000,
                allocated=1000,
                unmet=0,
                created_at=datetime.utcnow() - timedelta(hours=2),
            ),
            AllocationRecord(
                run_id="run-fixture",
                zone_id=zone.id,
                relief_center_id=fixture_depot.id,
                resource_category="food",
                demanded=1000,
                allocated=900,
                unmet=0,
                created_at=datetime.utcnow() - timedelta(minutes=5),
            ),
            AllocationRecord(
                run_id="run-fixture",
                zone_id=zone.id,
                relief_center_id=live_depot.id,
                resource_category="food",
                demanded=1000,
                allocated=100,
                unmet=0,
                created_at=datetime.utcnow() - timedelta(minutes=5),
            ),
        ]
    )
    db_session.flush()

    response = client.get("/analytics/reports")
    assert response.status_code == 200
    body = response.json()

    trend_runs = {row["run_id"] for row in body["coverage_trend"]}
    assert "run-clean" in trend_runs
    assert "run-fixture" not in trend_runs

    # Without the run-level exclusion the fixture run would win "latest" and
    # report 900 units of phantom unmet demand for this zone.
    zone_rows = [
        row for row in body["critical_zones"] if row["zone_name"] == zone.zone_name
    ]
    assert zone_rows == []


def test_critical_zones_only_lists_real_gaps(db_session):
    """Zero-unmet zones must not pad out the 'highest unmet demand' list."""
    _seed_report_data(db_session)
    response = client.get("/analytics/reports")
    assert response.status_code == 200
    body = response.json()
    assert body["critical_zones"], "expected at least one zone with a gap"
    assert all(row["unmet"] > 0 for row in body["critical_zones"])


def test_situation_report_contains_real_disaster_data(db_session):
    disaster, zone, depot = _seed_report_data(db_session)
    response = client.get(f"/analytics/situation-report/{disaster.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["disaster"]["title"] == "Earthquake in Chennai"
    assert body["disaster"]["event_id"] == "EQ-TEST-SITREP-1"
    assert any(row["zone_id"] == zone.id for row in body["affected_zones"])
    assert any(row["depot_name"] == depot.name for row in body["allocations"])
    assert any(row["mission_code"] == "MSN-SITREP-TEST" for row in body["missions"])
    assert any(row["assigned_to"] == "Alpha Response" for row in body["missions"])
    zone_demand = next(row for row in body["predicted_demand"] if row["zone_id"] == zone.id)
    food = next(item for item in zone_demand["categories"] if item["category"] == "food")
    assert food["demanded"] == 100
    assert food["allocated"] == 80

    html_resp = client.get(f"/analytics/situation-report/{disaster.id}/html")
    assert html_resp.status_code == 200
    html = html_resp.text
    assert "Earthquake in Chennai" in html
    assert "EQ-TEST-SITREP-1" in html
    assert "Chennai Relief Camp" in html
    assert "MSN-SITREP-TEST" in html
    assert "Alpha Response" in html
    assert "Print / Save as PDF" not in html
    assert "<button" not in html


def test_situation_report_missing_disaster(db_session):
    response = client.get("/analytics/situation-report/999999")
    assert response.status_code == 404


def test_allocation_reports_excludes_non_active_depots(db_session):
    """A run mixing live and quarantined supply is dropped, not half-counted.

    Zeroing only the quarantined depot's units while keeping the run's full
    demand reported a coverage collapse that never happened.
    """
    zone = DisasterZone(
        zone_name="Depot Filter Zone",
        disaster_type="EQ",
        severity="High",
        latitude=13.15,
        longitude=80.31,
        affected_population=4000,
        status="Active",
        operational_priority="High",
    )
    live_depot = ReliefCenter(
        name="Live Depot",
        address="Chennai",
        latitude=13.08,
        longitude=80.27,
        capacity=1000,
        available_capacity=900,
        status="Active",
    )
    quarantined = ReliefCenter(
        name="M3 Depot deadbeef",
        address="Nowhere",
        latitude=13.09,
        longitude=80.28,
        capacity=1000,
        available_capacity=900,
        status="Quarantined",
    )
    db_session.add_all([zone, live_depot, quarantined])
    db_session.flush()
    db_session.add_all(
        [
            AllocationRecord(
                run_id="run-depot-filter",
                zone_id=zone.id,
                relief_center_id=live_depot.id,
                resource_category="medical",
                demanded=300,
                allocated=100,
                unmet=200,
            ),
            AllocationRecord(
                run_id="run-depot-filter",
                zone_id=zone.id,
                relief_center_id=quarantined.id,
                resource_category="medical",
                demanded=300,
                allocated=50_000,
                unmet=200,
            ),
        ]
    )
    db_session.flush()

    body = client.get("/analytics/reports").json()
    trend_runs = {row["run_id"] for row in body["coverage_trend"]}
    assert "run-depot-filter" not in trend_runs
    zone_names = [row["zone_name"] for row in body["critical_zones"]]
    assert "Depot Filter Zone" not in zone_names


def test_situation_report_html_print_bar_is_optional(db_session):
    disaster, _zone, _depot = _seed_report_data(db_session)

    from app.services.analytics.situation_report_service import (
        get_situation_report,
        render_situation_report_html,
    )

    payload = get_situation_report(db_session, disaster.id)
    with_bar = render_situation_report_html(payload, include_print_bar=True)
    assert "Print / Save as PDF" in with_bar
    assert ".print-bar { display: none !important; }" in with_bar

    downloaded = client.get(f"/analytics/situation-report/{disaster.id}/html").text
    assert "Print / Save as PDF" not in downloaded
    assert '<div class="print-bar"' not in downloaded
    assert "<button" not in downloaded
    assert "Earthquake in Chennai" in downloaded
    assert f"(#{disaster.id})" in downloaded

    bare_html = client.get(
        f"/analytics/situation-report/{disaster.id}/html?bare=true"
    ).text
    assert "Print / Save as PDF" not in bare_html
    assert '<div class="print-bar"' not in bare_html


def test_situation_report_filename_and_scope_are_disaster_specific(db_session):
    disaster, _zone, _depot = _seed_report_data(db_session)
    response = client.get(f"/analytics/situation-report/{disaster.id}/html")
    disposition = response.headers["content-disposition"]
    assert f"DRMS-situation-report-{disaster.id}-EQ-TEST-SITREP-1.html" in disposition
    assert response.headers["cache-control"].startswith("no-store")
    assert f"Incident #{disaster.id}" in response.text

    payload = client.get(f"/analytics/situation-report/{disaster.id}").json()
    assert payload["scope"]["radius_km"] == 150.0
    assert payload["scope"]["zones_reported"] == len(payload["affected_zones"])


def test_fixture_zone_name_excluded_even_if_marked_active(db_session):
    """Name fence: pytest leftovers must not re-enter reports if status is Active."""
    fixture = DisasterZone(
        zone_name="M3 Test Zone",
        disaster_type="EQ",
        severity="Critical",
        latitude=13.12,
        longitude=80.30,
        affected_population=100,
        status="Active",
        operational_priority="Critical",
    )
    real = DisasterZone(
        zone_name="EQ-202608071200-Zone-99",
        disaster_type="EQ",
        severity="High",
        latitude=13.11,
        longitude=80.29,
        affected_population=4000,
        status="Active",
        operational_priority="High",
    )
    depot = ReliefCenter(
        name="Chennai Relief Camp",
        address="Chennai",
        latitude=13.08,
        longitude=80.27,
        capacity=1000,
        available_capacity=800,
        status="Active",
    )
    db_session.add_all([fixture, real, depot])
    db_session.flush()
    db_session.add_all(
        [
            AllocationRecord(
                run_id="run-fixture-active",
                zone_id=fixture.id,
                relief_center_id=depot.id,
                resource_category="food",
                demanded=50_000,
                allocated=0,
                unmet=50_000,
            ),
            AllocationRecord(
                run_id="run-real-gap",
                zone_id=real.id,
                relief_center_id=depot.id,
                resource_category="food",
                demanded=400,
                allocated=100,
                unmet=300,
            ),
        ]
    )
    db_session.flush()

    body = client.get("/analytics/reports").json()
    names = [row["zone_name"] for row in body["critical_zones"]]
    assert "M3 Test Zone" not in names
    assert "EQ-202608071200-Zone-99" in names
    assert not any("run-fixture-active" == row["run_id"] for row in body["coverage_trend"])

