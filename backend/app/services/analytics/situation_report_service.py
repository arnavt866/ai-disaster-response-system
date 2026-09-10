"""Post-event situation reports for a single disaster (debrief / accountability)."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.allocation_record import AllocationRecord
from app.models.disaster_zone import DisasterZone
from app.models.field_team import FieldTeam
from app.models.mission import Mission
from app.models.relief_center import ReliefCenter
from app.services.advisory_service import get_disaster_zone_advisory
from app.services.analytics.analytics_service import _latest_run_keys, unmet_from
from app.services.disaster_service import get_disaster_by_id


def _safe_json(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _latest_zone_allocations(db: Session, zone_ids: list[int]) -> list[dict[str, Any]]:
    if not zone_ids:
        return []
    latest_run_keys = _latest_run_keys(db)
    rows = (
        db.query(
            AllocationRecord.zone_id,
            AllocationRecord.relief_center_id,
            AllocationRecord.resource_category,
            latest_run_keys.c.demanded.label("demanded"),
            func.sum(AllocationRecord.allocated).label("allocated"),
            latest_run_keys.c.demanded.label("run_demanded"),
            latest_run_keys.c.allocated.label("run_allocated"),
            AllocationRecord.run_id,
            func.min(AllocationRecord.created_at).label("created_at"),
        )
        .join(
            latest_run_keys,
            (AllocationRecord.zone_id == latest_run_keys.c.zone_id)
            & (AllocationRecord.resource_category == latest_run_keys.c.resource_category)
            & (AllocationRecord.run_id == latest_run_keys.c.run_id),
        )
        # Quarantined/Inactive depots are leftover fixtures, not real supply.
        .join(
            ReliefCenter,
            (ReliefCenter.id == AllocationRecord.relief_center_id)
            & (ReliefCenter.status == "Active"),
        )
        .filter(AllocationRecord.zone_id.in_(zone_ids))
        .group_by(
            AllocationRecord.zone_id,
            AllocationRecord.relief_center_id,
            AllocationRecord.resource_category,
            AllocationRecord.run_id,
            latest_run_keys.c.demanded,
            latest_run_keys.c.allocated,
        )
        .all()
    )

    depot_ids = {int(row.relief_center_id) for row in rows if row.relief_center_id}
    depots = (
        db.query(ReliefCenter).filter(ReliefCenter.id.in_(depot_ids)).all()
        if depot_ids
        else []
    )
    depot_map = {depot.id: depot.name for depot in depots}

    results = []
    for row in rows:
        results.append(
            {
                "zone_id": row.zone_id,
                "relief_center_id": row.relief_center_id,
                "depot_name": depot_map.get(row.relief_center_id) or f"Depot {row.relief_center_id}",
                "resource_category": row.resource_category,
                "demanded": round(float(row.demanded or 0.0), 2),
                "allocated": round(float(row.allocated or 0.0), 2),
                "unmet": round(unmet_from(row.run_demanded, row.run_allocated), 2),
                "run_id": row.run_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    results.sort(key=lambda item: (item["zone_id"], item["resource_category"], item["depot_name"]))
    return results


def get_situation_report(
    db: Session,
    disaster_id: int,
    *,
    radius_km: float = 150.0,
    zone_limit: int = 20,
) -> dict[str, Any]:
    disaster = get_disaster_by_id(db, disaster_id)
    if disaster is None:
        raise ValueError(f"Disaster {disaster_id} not found")

    advisory = get_disaster_zone_advisory(
        db,
        disaster_id,
        radius_km=radius_km,
        limit=zone_limit,
    )
    advisory_rows = advisory.get("advisories") or []
    zone_ids = [int(row["zone_id"]) for row in advisory_rows if row.get("zone_id") is not None]
    zones = (
        db.query(DisasterZone)
        .filter(DisasterZone.id.in_(zone_ids), DisasterZone.status == "Active")
        .all()
        if zone_ids
        else []
    )
    zone_map = {zone.id: zone for zone in zones}
    advisory_rows = [row for row in advisory_rows if row["zone_id"] in zone_map]
    zone_ids = [row["zone_id"] for row in advisory_rows]

    affected_zones = []
    for row in advisory_rows:
        zone = zone_map.get(row["zone_id"])
        affected_zones.append(
            {
                "zone_id": row["zone_id"],
                "zone_name": row.get("zone_name") or (zone.zone_name if zone else f"Zone {row['zone_id']}"),
                "disaster_type": zone.disaster_type if zone else row.get("zone_type"),
                "severity": zone.severity if zone else row.get("zone_severity"),
                "operational_priority": zone.operational_priority if zone else None,
                "status": zone.status if zone else row.get("zone_status"),
                "affected_population": int(zone.affected_population or 0) if zone else 0,
                "latitude": zone.latitude if zone else None,
                "longitude": zone.longitude if zone else None,
                "distance_km": row.get("distance_km"),
                "advisory_level": row.get("advisory_level"),
                "advisory_score": row.get("advisory_score"),
                "type_match": row.get("type_match"),
            }
        )

    allocations = _latest_zone_allocations(db, zone_ids)

    demand_by_zone: dict[int, dict[str, dict[str, float]]] = {}
    for row in allocations:
        zone_bucket = demand_by_zone.setdefault(row["zone_id"], {})
        cat_bucket = zone_bucket.setdefault(
            row["resource_category"],
            {"demanded": 0.0, "allocated": 0.0, "unmet": 0.0},
        )
        cat_bucket["demanded"] = max(cat_bucket["demanded"], row["demanded"])
        cat_bucket["allocated"] += row["allocated"]
        cat_bucket["unmet"] = max(cat_bucket["unmet"], row["unmet"])

    predicted_demand = []
    for zone_row in affected_zones:
        categories = demand_by_zone.get(zone_row["zone_id"], {})
        if not categories:
            predicted_demand.append(
                {
                    "zone_id": zone_row["zone_id"],
                    "zone_name": zone_row["zone_name"],
                    "categories": [],
                    "total_demanded": 0.0,
                    "note": "No persisted allocation demand for this zone yet.",
                }
            )
            continue
        category_rows = [
            {
                "category": category,
                "demanded": round(totals["demanded"], 2),
                "allocated": round(totals["allocated"], 2),
                "unmet": round(totals["unmet"], 2),
            }
            for category, totals in sorted(categories.items())
        ]
        predicted_demand.append(
            {
                "zone_id": zone_row["zone_id"],
                "zone_name": zone_row["zone_name"],
                "categories": category_rows,
                "total_demanded": round(sum(item["demanded"] for item in category_rows), 2),
                "note": "Demand figures are the ML estimates used by the latest allocation run.",
            }
        )

    missions = []
    if zone_ids:
        mission_rows = (
            db.query(Mission)
            .filter(Mission.zone_id.in_(zone_ids))
            .order_by(Mission.created_at.desc())
            .all()
        )
        team_ids = {row.field_team_id for row in mission_rows if row.field_team_id}
        depot_ids = {row.relief_center_id for row in mission_rows if row.relief_center_id}
        teams = (
            db.query(FieldTeam).filter(FieldTeam.id.in_(team_ids)).all() if team_ids else []
        )
        depots = (
            db.query(ReliefCenter).filter(ReliefCenter.id.in_(depot_ids)).all()
            if depot_ids
            else []
        )
        team_map = {team.id: team.team_name for team in teams}
        depot_map = {depot.id: depot.name for depot in depots}
        for row in mission_rows:
            missions.append(
                {
                    "id": row.id,
                    "mission_code": row.mission_code,
                    "zone_id": row.zone_id,
                    "zone_name": zone_map[row.zone_id].zone_name
                    if row.zone_id in zone_map
                    else f"Zone {row.zone_id}",
                    "priority": row.priority,
                    "status": row.status,
                    "field_team_id": row.field_team_id,
                    "assigned_to": team_map.get(row.field_team_id),
                    "relief_center_id": row.relief_center_id,
                    "depot_name": depot_map.get(row.relief_center_id),
                    "route_distance_km": row.route_distance_km,
                    "route_eta_hours": row.route_eta_hours,
                    "route_status": row.route_status,
                    "resources": _safe_json(row.resources_payload),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )

    category_totals: dict[str, dict[str, float]] = {}
    for zone_cats in demand_by_zone.values():
        for category, totals in zone_cats.items():
            bucket = category_totals.setdefault(
                category.lower(),
                {"allocated": 0.0, "demanded": 0.0, "unmet": 0.0},
            )
            bucket["allocated"] += totals["allocated"]
            bucket["demanded"] += totals["demanded"]
            bucket["unmet"] += totals["unmet"]

    category_breakdown = [
        {
            "category": category,
            "allocated": round(totals["allocated"], 2),
            "demanded": round(totals["demanded"], 2),
            "unmet": round(totals["unmet"], 2),
        }
        for category, totals in sorted(category_totals.items())
    ]

    zone_unmet = []
    for zone_row in affected_zones:
        cats = demand_by_zone.get(zone_row["zone_id"], {})
        unmet = round(sum(item["unmet"] for item in cats.values()), 2)
        allocated = round(sum(item["allocated"] for item in cats.values()), 2)
        demanded = round(sum(item["demanded"] for item in cats.values()), 2)
        zone_unmet.append(
            {
                "zone_id": zone_row["zone_id"],
                "zone_name": zone_row["zone_name"],
                "priority": zone_row["operational_priority"] or "Unknown",
                "unmet": unmet,
                "allocated": allocated,
                "demanded": demanded,
            }
        )
    zone_unmet.sort(key=lambda row: (-row["unmet"], -row["demanded"]))

    total_allocated = round(sum(item["allocated"] for item in category_breakdown), 2)
    total_demanded = round(sum(item["demanded"] for item in category_breakdown), 2)
    total_unmet = round(sum(item["unmet"] for item in category_breakdown), 2)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "generated_at": generated_at,
        "report_type": "post_event_situation_report",
        "disaster": {
            "id": disaster.id,
            "event_id": disaster.event_id,
            "title": disaster.title,
            "disaster_type": disaster.disaster_type,
            "severity": disaster.severity,
            "status": disaster.status,
            "source": disaster.source,
            "location": disaster.location,
            "latitude": disaster.latitude,
            "longitude": disaster.longitude,
            "magnitude": disaster.magnitude,
            "event_time": disaster.event_time.isoformat() if disaster.event_time else None,
        },
        "scope": {
            "radius_km": radius_km,
            "zone_limit": zone_limit,
            "zones_in_radius": advisory.get("zones_scored", 0),
            "zones_reported": len(affected_zones),
        },
        "affected_zones": affected_zones,
        "predicted_demand": predicted_demand,
        "allocations": allocations,
        "missions": missions,
        "charts": {
            "category_breakdown": category_breakdown,
            "zone_unmet": zone_unmet[:8],
        },
        "totals": {
            "affected_zones": len(affected_zones),
            "affected_population": sum(row["affected_population"] for row in affected_zones),
            "allocated": total_allocated,
            "demanded": total_demanded,
            "unmet": total_unmet,
            "coverage_ratio": round(
                (total_allocated / total_demanded) if total_demanded else 0.0,
                4,
            ),
            "missions": len(missions),
        },
        "data_source": "database",
        "notes": [
            "Affected zones are the nearest active operational zones scored against this incident.",
            "Predicted demand is the ML demand the allocation engine used on the latest persisted run.",
            "Allocated-by is the supplying relief depot; assigned-to is the field team on the mission.",
            "Incidents that share the same coordinates share the same nearby-zone set; "
            "Event ID and Incident # identify which feed row this file belongs to.",
        ]
        + (
            [
                f"No active operational zones fall within {radius_km:g} km of this incident, "
                "so demand, allocation, and mission sections are empty by design."
            ]
            if not affected_zones
            else []
        ),
    }


def _bar_chart_svg(
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    series: list[tuple[str, str]],
    width: int = 640,
    height: int = 220,
) -> str:
    if not rows:
        return '<p class="empty">No chart data for this incident.</p>'
    padding_left = 120
    padding_right = 24
    padding_top = 16
    padding_bottom = 36
    plot_w = width - padding_left - padding_right
    plot_h = height - padding_top - padding_bottom
    max_value = max(
        (float(row.get(key) or 0) for row in rows for key, _color in series),
        default=0,
    ) or 1
    group_h = plot_h / max(len(rows), 1)
    bar_h = max(6.0, (group_h - 8) / max(len(series), 1))
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Allocation chart">'
    ]
    for index, row in enumerate(rows):
        y0 = padding_top + index * group_h
        label = html.escape(str(row.get(label_key) or ""))
        parts.append(
            f'<text x="8" y="{y0 + group_h / 2 + 4}" class="tick">{label}</text>'
        )
        for series_index, (key, color) in enumerate(series):
            value = float(row.get(key) or 0)
            bar_w = (value / max_value) * plot_w
            y = y0 + 4 + series_index * (bar_h + 2)
            parts.append(
                f'<rect x="{padding_left}" y="{y:.1f}" width="{bar_w:.1f}" '
                f'height="{bar_h:.1f}" fill="{color}" rx="2"/>'
            )
            if value > 0:
                parts.append(
                    f'<text x="{padding_left + bar_w + 6:.1f}" y="{y + bar_h - 1:.1f}" '
                    f'class="value">{value:,.0f}</text>'
                )
    parts.append("</svg>")
    legend = "".join(
        f'<span class="legend-item"><i style="background:{color}"></i>{html.escape(key)}</span>'
        for key, color in series
    )
    return f'<div class="chart-wrap">{"".join(parts)}<div class="legend">{legend}</div></div>'


def render_situation_report_html(
    payload: dict[str, Any],
    *,
    include_print_bar: bool = True,
) -> str:
    disaster = payload["disaster"]
    totals = payload["totals"]
    generated = payload.get("generated_at") or ""
    title = html.escape(disaster.get("title") or "Untitled incident")
    event_id = html.escape(str(disaster.get("event_id") or disaster.get("id")))

    scope = payload.get("scope") or {}
    radius = scope.get("radius_km")
    scope_line = (
        f"Scope: operational zones within {radius:g} km of "
        f"{disaster.get('latitude')}, {disaster.get('longitude')} · "
        f"{totals['affected_zones']} zone(s) matched"
        if radius is not None
        else f"{totals['affected_zones']} zone(s) matched"
    )

    # The button is removed from the DOM during printing so no PDF export path
    # (print CSS, headless renderer, or a viewer that ignores @media print)
    # can bake it into the output.
    print_bar_html = (
        """<div class="print-bar" id="print-bar">
      <button type="button" onclick="printClean()">Print / Save as PDF</button>
    </div>
    <script>
      function hidePrintBar() {
        var bar = document.getElementById('print-bar');
        if (bar) bar.setAttribute('hidden', 'hidden');
      }
      function showPrintBar() {
        var bar = document.getElementById('print-bar');
        if (bar) bar.removeAttribute('hidden');
      }
      function printClean() {
        hidePrintBar();
        window.print();
      }
      window.addEventListener('beforeprint', hidePrintBar);
      window.addEventListener('afterprint', showPrintBar);
      if (window.matchMedia) {
        var mq = window.matchMedia('print');
        var onChange = function (e) { e.matches ? hidePrintBar() : showPrintBar(); };
        mq.addEventListener ? mq.addEventListener('change', onChange) : mq.addListener(onChange);
      }
    </script>"""
        if include_print_bar
        else ""
    )

    zone_rows = []
    for row in payload["affected_zones"]:
        zone_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('zone_name') or ''))}</td>"
            f"<td>{html.escape(str(row.get('severity') or '—'))}</td>"
            f"<td>{html.escape(str(row.get('operational_priority') or '—'))}</td>"
            f"<td class='num'>{int(row.get('affected_population') or 0):,}</td>"
            f"<td class='num'>{row.get('distance_km') if row.get('distance_km') is not None else '—'}</td>"
            f"<td>{html.escape(str(row.get('advisory_level') or '—'))}</td>"
            "</tr>"
        )

    demand_rows = []
    for zone in payload["predicted_demand"]:
        if not zone["categories"]:
            demand_rows.append(
                "<tr>"
                f"<td>{html.escape(zone['zone_name'])}</td>"
                "<td colspan='4' class='muted'>No persisted ML demand for this zone yet.</td>"
                "</tr>"
            )
            continue
        for item in zone["categories"]:
            demand_rows.append(
                "<tr>"
                f"<td>{html.escape(zone['zone_name'])}</td>"
                f"<td>{html.escape(str(item['category']))}</td>"
                f"<td class='num'>{item['demanded']:,.1f}</td>"
                f"<td class='num'>{item['allocated']:,.1f}</td>"
                f"<td class='num'>{item['unmet']:,.1f}</td>"
                "</tr>"
            )

    allocation_rows = []
    for row in payload["allocations"]:
        allocation_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['resource_category']))}</td>"
            f"<td>{html.escape(str(row['depot_name']))}</td>"
            f"<td class='num'>{row['demanded']:,.1f}</td>"
            f"<td class='num'>{row['allocated']:,.1f}</td>"
            f"<td class='num'>{row['unmet']:,.1f}</td>"
            f"<td class='num'>{row['zone_id']}</td>"
            "</tr>"
        )

    mission_rows = []
    for row in payload["missions"]:
        route = "—"
        if row.get("route_distance_km") is not None:
            route = f"{row['route_distance_km']:.2f} km"
            if row.get("route_eta_hours") is not None:
                route += f" / {row['route_eta_hours']:.2f} h"
        assigned = row.get("assigned_to") or "Unassigned"
        mission_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['mission_code']))}</td>"
            f"<td>{html.escape(str(row['zone_name']))}</td>"
            f"<td>{html.escape(str(assigned))}</td>"
            f"<td>{html.escape(str(row.get('depot_name') or '—'))}</td>"
            f"<td>{html.escape(str(row.get('status') or '—'))}</td>"
            f"<td>{html.escape(route)}</td>"
            "</tr>"
        )

    category_svg = _bar_chart_svg(
        payload["charts"]["category_breakdown"],
        label_key="category",
        series=[("allocated", "#0f766e"), ("unmet", "#dc2626")],
    )
    unmet_svg = _bar_chart_svg(
        payload["charts"]["zone_unmet"],
        label_key="zone_name",
        series=[("unmet", "#c2410c"), ("allocated", "#0f766e")],
    )

    def _cell(label: str, value: Any) -> str:
        return (
            f"<div class='meta'><dt>{html.escape(label)}</dt>"
            f"<dd>{html.escape(str(value if value not in (None, '') else '—'))}</dd></div>"
        )

    notes = "".join(f"<li>{html.escape(note)}</li>" for note in payload.get("notes") or [])

    if include_print_bar:
        print_bar_css = """
    .print-bar { display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px; }
    .print-bar button { background: var(--accent); color: white; border: 0; padding: 8px 14px; font-weight: 600; cursor: pointer; }
    @media print {
      body { background: white; }
      .sheet { margin: 0; border: 0; padding: 0; max-width: none; }
      .print-bar { display: none !important; }
    }
    .print-bar[hidden] { display: none !important; }
"""
    else:
        print_bar_css = """
    @media print {
      body { background: white; }
      .sheet { margin: 0; border: 0; padding: 0; max-width: none; }
    }
"""

    disaster_id = disaster.get("id")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Situation Report — {title} — {event_id} (#{disaster_id})</title>
  <style>
    :root {{
      --ink: #0f172a;
      --muted: #475569;
      --line: #cbd5e1;
      --accent: #0f766e;
      --paper: #ffffff;
      --tint: #f0fdfa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #f8fafc;
      font: 16px/1.5 "Segoe UI", system-ui, sans-serif;
    }}
    .sheet {{
      max-width: 920px;
      margin: 24px auto;
      background: var(--paper);
      border: 1px solid var(--line);
      padding: 32px 36px;
    }}
    header {{
      border-bottom: 3px solid var(--accent);
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    .kicker {{
      color: var(--accent);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1 {{ margin: 6px 0 4px; font-size: 28px; }}
    h2 {{
      margin: 28px 0 10px;
      font-size: 18px;
      color: var(--accent);
      border-bottom: 1px solid var(--line);
      padding-bottom: 4px;
    }}
    .sub {{ color: var(--muted); margin: 0; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 24px;
      margin: 16px 0;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0 8px;
    }}
    .kpi {{
      background: var(--tint);
      border: 1px solid #99f6e4;
      padding: 10px 12px;
    }}
    .kpi span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .kpi strong {{ font-size: 22px; }}
    .meta dt {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .meta dd {{ margin: 0 0 6px; font-weight: 600; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 7px 6px;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .muted, .empty {{ color: var(--muted); }}
    .chart {{ width: 100%; height: auto; }}
    .tick, .value {{ font-size: 11px; fill: #334155; }}
    .legend {{ display: flex; gap: 14px; margin-top: 6px; font-size: 13px; color: var(--muted); }}
    .legend i {{ display: inline-block; width: 10px; height: 10px; margin-right: 6px; }}
    footer {{
      margin-top: 28px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 13px;
    }}
    {print_bar_css}
  </style>
</head>
<body>
  <article class="sheet">
    {print_bar_html}
    <header>
      <p class="kicker">DRMS Command Center · Post-event situation report</p>
      <h1>{title}</h1>
      <p class="sub">Event {event_id} · Incident #{disaster.get('id')} · Generated {html.escape(generated)}</p>
      <p class="sub">{html.escape(scope_line)}</p>
    </header>

    <section>
      <h2>1. Incident summary</h2>
      <div class="kpis">
        <div class="kpi"><span>Affected zones</span><strong>{totals['affected_zones']}</strong></div>
        <div class="kpi"><span>Population</span><strong>{int(totals['affected_population'] or 0):,}</strong></div>
        <div class="kpi"><span>Coverage</span><strong>{totals['coverage_ratio'] * 100:.1f}%</strong></div>
        <div class="kpi"><span>Unmet demand</span><strong>{totals['unmet']:,.0f}</strong></div>
      </div>
      <div class="grid">
        {_cell("Type", disaster.get("disaster_type"))}
        {_cell("Severity", disaster.get("severity"))}
        {_cell("Status", disaster.get("status"))}
        {_cell("Source", disaster.get("source"))}
        {_cell("Location", disaster.get("location"))}
        {_cell("Coordinates", f"{disaster.get('latitude')}, {disaster.get('longitude')}")}
        {_cell("Magnitude", disaster.get("magnitude"))}
        {_cell("Event time", disaster.get("event_time"))}
      </div>
    </section>

    <section>
      <h2>2. Affected zones</h2>
      <table>
        <thead>
          <tr>
            <th>Zone</th><th>Severity</th><th>Priority</th>
            <th class="num">Population</th><th class="num">Distance (km)</th><th>Advisory</th>
          </tr>
        </thead>
        <tbody>
          {''.join(zone_rows) or '<tr><td colspan="6" class="muted">No nearby active zones scored for this incident.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section>
      <h2>3. AI-predicted demand (used by allocation)</h2>
      <table>
        <thead>
          <tr>
            <th>Zone</th><th>Category</th>
            <th class="num">Predicted</th><th class="num">Allocated</th><th class="num">Unmet</th>
          </tr>
        </thead>
        <tbody>
          {''.join(demand_rows) or '<tr><td colspan="5" class="muted">No demand records for nearby zones.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section>
      <h2>4. Allocation results</h2>
      <p class="muted">Allocated totals {totals['allocated']:,.1f} of {totals['demanded']:,.1f} demanded units. Supplying depot is listed per flow.</p>
      <table>
        <thead>
          <tr>
            <th>Category</th><th>Supplied by (depot)</th>
            <th class="num">Demanded</th><th class="num">Allocated</th>
            <th class="num">Unmet</th><th class="num">Zone ID</th>
          </tr>
        </thead>
        <tbody>
          {''.join(allocation_rows) or '<tr><td colspan="6" class="muted">No persisted allocation runs for these zones.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section>
      <h2>5. Generated routes &amp; missions</h2>
      <table>
        <thead>
          <tr>
            <th>Mission</th><th>Zone</th><th>Assigned to</th>
            <th>Depot</th><th>Status</th><th>Route</th>
          </tr>
        </thead>
        <tbody>
          {''.join(mission_rows) or '<tr><td colspan="6" class="muted">No missions recorded for these zones.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section>
      <h2>6. Charts</h2>
      <h3>Resource category — allocated vs unmet</h3>
      {category_svg}
      <h3>Highest unmet demand by zone</h3>
      {unmet_svg}
    </section>

    <footer>
      <p>DRMS situation report for donor accountability and operational debrief. Figures are taken from the live operational database, not a static demo fixture.</p>
      <ul>{notes}</ul>
    </footer>
  </article>
</body>
</html>
"""
