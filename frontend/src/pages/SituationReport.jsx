import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { getSituationReport } from "../api/analytics"
import DownloadReportButton from "../components/ui/DownloadReportButton"
import CategoryBreakdownChart from "../components/Charts/CategoryBreakdownChart"
import CriticalZonesChart from "../components/Charts/CriticalZonesChart"
import PageHeader from "../components/ui/PageHeader"
import Badge from "../components/ui/Badge"
import { ErrorState } from "../components/ui/StateMessage"
import { severityBadge } from "../utils/badgeUtils"
import { formatDisasterType, formatEventTime } from "../utils/disasterHelpers"
import { formatRouteDistanceKm } from "../utils/routeUtils"

export default function SituationReport() {
  const { disasterId } = useParams()
  const [report, setReport] = useState(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getSituationReport(disasterId)
      .then((payload) => {
        if (!cancelled) setReport(payload)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [disasterId])

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Situation Report" subtitle="Loading incident dossier…" />
        <p className="ops-muted">Assembling zones, demand, allocations, and routes…</p>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="space-y-3">
        <PageHeader title="Situation Report" />
        <ErrorState title="Unable to build situation report" message={error || "No data"} />
      </div>
    )
  }

  const disaster = report.disaster
  const totals = report.totals

  return (
    <div className="space-y-3 print:space-y-4">
      <PageHeader
        title={disaster.title || "Situation Report"}
        subtitle={`${formatDisasterType(disaster.disaster_type)} · ${disaster.event_id} · generated ${formatEventTime(report.generated_at)}`}
        actions={
          <div className="flex flex-wrap gap-2 print:hidden">
            <DownloadReportButton disasterId={disaster.id} />
            <button type="button" className="ops-btn border border-[var(--border)]" onClick={() => window.print()}>
              Print / Save as PDF
            </button>
            <Link to="/disasters" className="ops-btn border border-[var(--border)]">
              Back to incidents
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="ops-card p-3">
          <p className="ops-section-label">Affected zones</p>
          <p className="text-xl font-bold">{totals.affected_zones}</p>
        </div>
        <div className="ops-card p-3">
          <p className="ops-section-label">Population</p>
          <p className="text-xl font-bold">{(totals.affected_population || 0).toLocaleString()}</p>
        </div>
        <div className="ops-card p-3">
          <p className="ops-section-label">Coverage</p>
          <p className="text-xl font-bold">{((totals.coverage_ratio || 0) * 100).toFixed(1)}%</p>
        </div>
        <div className="ops-card p-3">
          <p className="ops-section-label">Unmet demand</p>
          <p className="text-xl font-bold">{(totals.unmet || 0).toLocaleString()}</p>
        </div>
      </div>

      <div className="ops-card p-3">
        <h2 className="mb-2 ops-section-title">Incident</h2>
        <dl className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <div><dt className="ops-muted">Location</dt><dd>{disaster.location || "—"}</dd></div>
          <div><dt className="ops-muted">Severity</dt><dd><Badge variant={severityBadge(disaster.severity)}>{disaster.severity || "—"}</Badge></dd></div>
          <div><dt className="ops-muted">Status</dt><dd>{disaster.status || "—"}</dd></div>
          <div><dt className="ops-muted">Source</dt><dd>{disaster.source || "—"}</dd></div>
          <div><dt className="ops-muted">Coordinates</dt><dd>{disaster.latitude}, {disaster.longitude}</dd></div>
          <div><dt className="ops-muted">Event time</dt><dd>{formatEventTime(disaster.event_time)}</dd></div>
        </dl>
      </div>

      <div className="ops-card p-3 overflow-x-auto">
        <h2 className="mb-2 ops-section-title">Affected zones</h2>
        <table className="ops-table w-full">
          <thead>
            <tr className="border-b border-[var(--border)] text-left">
              <th>Zone</th>
              <th>Severity</th>
              <th>Priority</th>
              <th>Population</th>
              <th>Distance</th>
              <th>Advisory</th>
            </tr>
          </thead>
          <tbody>
            {report.affected_zones.map((zone) => (
              <tr key={zone.zone_id} className="border-b border-[var(--border)]">
                <td>{zone.zone_name}</td>
                <td>{zone.severity || "—"}</td>
                <td><Badge variant={severityBadge(zone.operational_priority)}>{zone.operational_priority || "—"}</Badge></td>
                <td>{(zone.affected_population || 0).toLocaleString()}</td>
                <td>{zone.distance_km != null ? `${zone.distance_km} km` : "—"}</td>
                <td>{zone.advisory_level || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="ops-card p-3 overflow-x-auto">
        <h2 className="mb-2 ops-section-title">AI-predicted demand</h2>
        <p className="mb-2 ops-muted">ML demand used by the latest persisted allocation run for these zones.</p>
        <table className="ops-table w-full">
          <thead>
            <tr className="border-b border-[var(--border)] text-left">
              <th>Zone</th>
              <th>Category</th>
              <th>Predicted</th>
              <th>Allocated</th>
              <th>Unmet</th>
            </tr>
          </thead>
          <tbody>
            {report.predicted_demand.flatMap((zone) =>
              zone.categories.length === 0 ? (
                <tr key={zone.zone_id} className="border-b border-[var(--border)]">
                  <td>{zone.zone_name}</td>
                  <td colSpan={4} className="ops-muted">{zone.note}</td>
                </tr>
              ) : (
                zone.categories.map((item) => (
                  <tr key={`${zone.zone_id}-${item.category}`} className="border-b border-[var(--border)]">
                    <td>{zone.zone_name}</td>
                    <td>{item.category}</td>
                    <td>{item.demanded.toLocaleString()}</td>
                    <td>{item.allocated.toLocaleString()}</td>
                    <td>{item.unmet.toLocaleString()}</td>
                  </tr>
                ))
              ),
            )}
          </tbody>
        </table>
      </div>

      <div className="ops-card p-3 overflow-x-auto">
        <h2 className="mb-2 ops-section-title">Allocation results</h2>
        <table className="ops-table w-full">
          <thead>
            <tr className="border-b border-[var(--border)] text-left">
              <th>Category</th>
              <th>Supplied by</th>
              <th>Demanded</th>
              <th>Allocated</th>
              <th>Unmet</th>
              <th>Zone</th>
            </tr>
          </thead>
          <tbody>
            {report.allocations.length === 0 ? (
              <tr><td colSpan={6} className="ops-muted">No persisted allocation for these zones.</td></tr>
            ) : (
              report.allocations.map((row, index) => (
                <tr key={`${row.run_id}-${row.zone_id}-${row.resource_category}-${index}`} className="border-b border-[var(--border)]">
                  <td>{row.resource_category}</td>
                  <td>{row.depot_name}</td>
                  <td>{row.demanded.toLocaleString()}</td>
                  <td>{row.allocated.toLocaleString()}</td>
                  <td>{row.unmet.toLocaleString()}</td>
                  <td>{row.zone_id}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="ops-card p-3 overflow-x-auto">
        <h2 className="mb-2 ops-section-title">Routes & missions</h2>
        <table className="ops-table w-full">
          <thead>
            <tr className="border-b border-[var(--border)] text-left">
              <th>Mission</th>
              <th>Zone</th>
              <th>Assigned to</th>
              <th>Depot</th>
              <th>Status</th>
              <th>Route</th>
            </tr>
          </thead>
          <tbody>
            {report.missions.length === 0 ? (
              <tr><td colSpan={6} className="ops-muted">No missions for these zones.</td></tr>
            ) : (
              report.missions.map((mission) => (
                <tr key={mission.id} className="border-b border-[var(--border)]">
                  <td className="font-mono">{mission.mission_code}</td>
                  <td>{mission.zone_name}</td>
                  <td>{mission.assigned_to || "Unassigned"}</td>
                  <td>{mission.depot_name || "—"}</td>
                  <td>{mission.status}</td>
                  <td>{formatRouteDistanceKm(mission.route_distance_km)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="ops-card p-3">
          <h2 className="mb-2 ops-section-title">Category allocated vs unmet</h2>
          <CategoryBreakdownChart data={report.charts.category_breakdown} />
        </div>
        <div className="ops-card p-3">
          <h2 className="mb-2 ops-section-title">Highest unmet zones</h2>
          <CriticalZonesChart data={report.charts.zone_unmet} />
        </div>
      </div>
    </div>
  )
}
