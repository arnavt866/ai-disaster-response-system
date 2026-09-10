import { useEffect, useMemo, useState } from "react"
import { getDisasters } from "../api/disasters"
import { getAllocationReports, getDashboardMetrics } from "../api/analytics"
import { getMissions } from "../api/missions"
import PageHeader from "../components/ui/PageHeader"
import IncidentLineChart from "../components/Charts/IncidentLineChart"
import DistributionPieChart from "../components/Charts/DistributionPieChart"
import CoverageTrendChart from "../components/Charts/CoverageTrendChart"
import CategoryBreakdownChart from "../components/Charts/CategoryBreakdownChart"
import CriticalZonesChart from "../components/Charts/CriticalZonesChart"
import { ErrorState } from "../components/ui/StateMessage"
import InfoTooltip from "../components/ui/InfoTooltip"
import Badge from "../components/ui/Badge"
import { severityBadge } from "../utils/badgeUtils"
import { formatDisasterType } from "../utils/disasterHelpers"
import { formatRouteDistanceKm } from "../utils/routeUtils"

function formatDateKey(eventTime) {
  if (!eventTime) return "Unknown"
  const date = new Date(eventTime)
  if (Number.isNaN(date.getTime())) return "Unknown"
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
}

export default function Reports() {
  const [disasters, setDisasters] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [allocationReports, setAllocationReports] = useState(null)
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    Promise.all([getDisasters(), getDashboardMetrics(), getMissions(), getAllocationReports()])
      .then(([events, dashboard, missionRows, reportCharts]) => {
        if (!cancelled) {
          setDisasters(events)
          setMetrics(dashboard)
          setMissions(missionRows)
          setAllocationReports(reportCharts)
        }
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
  }, [])

  const typeBreakdown = useMemo(() => {
    const counts = {}
    disasters.forEach((event) => {
      const type = formatDisasterType(event.disaster_type)
      counts[type] = (counts[type] || 0) + 1
    })
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([name, value]) => ({ name, value }))
  }, [disasters])

  const priorityBreakdown = useMemo(
    () => (metrics?.severity_distribution || []).map((row) => ({ name: row.priority, value: row.count })),
    [metrics],
  )

  const incidentsOverTime = useMemo(() => {
    const counts = {}
    disasters.forEach((event) => {
      const key = formatDateKey(event.event_time)
      counts[key] = (counts[key] || 0) + 1
    })
    return Object.entries(counts)
      .map(([date, count]) => ({ date, count }))
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .slice(-14)
  }, [disasters])

  const recentMissions = useMemo(() => missions.slice(0, 8), [missions])
  const coverageTrend = allocationReports?.coverage_trend || []
  const categoryBreakdown = allocationReports?.category_breakdown || []
  const criticalZones = (allocationReports?.critical_zones || []).filter((zone) => {
    const name = String(zone.zone_name || "")
    const isFixture = /m3 test zone|tracking zone/i.test(name)
    return !isFixture && (zone.status == null || zone.status === "Active") && Number(zone.unmet) > 0
  })

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Operational Reports" subtitle="Analytics and incident summaries from live backend data" />
        <p className="ops-muted">Loading reports...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <PageHeader
        title="Operational Reports"
        subtitle="Post-event analytics from persisted allocation runs, zones, and missions"
      />
      {error && <ErrorState title="Unable to load reports" message={error} />}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="ops-card p-3">
          <p className="ops-section-label">Incidents</p>
          <p className="text-xl font-bold">{disasters.length}</p>
        </div>
        <div className="ops-card p-3">
          <p className="ops-section-label">Active Zones</p>
          <p className="text-xl font-bold">{metrics?.active_zones ?? 0}</p>
        </div>
        <div className="ops-card p-3">
          <p className="ops-section-label">Allocated Units</p>
          <p className="text-xl font-bold">{metrics?.allocated_resources ?? 0}</p>
        </div>
        <div className="ops-card p-3">
          <p className="inline-flex items-center ops-section-label">
            Unmet Demand
            <InfoTooltip
              label="About unmet demand"
              text="Resource units still needed after the latest allocation run — total demand minus what could be shipped from depots."
            />
          </p>
          <p className="text-xl font-bold">{metrics?.unmet_demand ?? 0}</p>
        </div>
      </div>

      <div className="ops-card p-3">
        <h2 className="mb-1 ops-section-title">Coverage ratio over allocation runs</h2>
        <p className="mb-2 ops-muted">
          Allocated vs unmet demand for each persisted optimizer run. Coverage % uses demanded as the denominator.
        </p>
        {coverageTrend.length === 0 ? (
          <p className="ops-muted">No allocation runs recorded yet. Run optimization from Allocation to populate this chart.</p>
        ) : (
          <CoverageTrendChart data={coverageTrend} />
        )}
      </div>

      {/* items-start stops the shorter chart card from stretching to match the
          taller zone table beside it, which left dead space under the bars. */}
      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-2">
        <div className="ops-card p-3">
          <h2 className="mb-1 ops-section-title">Resource category breakdown</h2>
          <p className="mb-2 ops-muted">Latest-run allocated totals versus remaining unmet demand.</p>
          {categoryBreakdown.length === 0 ? (
            <p className="ops-muted">No category allocation totals yet.</p>
          ) : (
            <CategoryBreakdownChart data={categoryBreakdown} />
          )}
        </div>

        <div className="ops-card p-3">
          <h2 className="mb-1 ops-section-title">Highest unmet demand by zone</h2>
          <p className="mb-2 ops-muted">
            Top gaps after the latest run. Bar colour follows operational priority.
          </p>
          {criticalZones.length === 0 ? (
            <p className="ops-muted">No zone-level unmet demand recorded.</p>
          ) : (
            <>
              <CriticalZonesChart data={criticalZones} />
              <div className="mt-2 overflow-x-auto">
                <table className="ops-table w-full">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-left">
                      <th>Zone</th>
                      <th>Priority</th>
                      <th>Population</th>
                      <th>Unmet</th>
                    </tr>
                  </thead>
                  <tbody>
                    {criticalZones.map((zone) => (
                      <tr key={zone.zone_id} className="border-b border-[var(--border)]">
                        <td>{zone.zone_name}</td>
                        <td>
                          <Badge variant={severityBadge(zone.priority)}>{zone.priority}</Badge>
                        </td>
                        <td>{(zone.affected_population || 0).toLocaleString()}</td>
                        <td>{zone.unmet.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="ops-card p-3">
        <h2 className="mb-2 ops-section-title">Incidents over time</h2>
        <IncidentLineChart data={incidentsOverTime} />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="ops-card p-3">
          <h2 className="mb-2 ops-section-title">Incident type breakdown</h2>
          {typeBreakdown.length === 0 ? (
            <p className="ops-muted">No disaster events recorded.</p>
          ) : (
            <DistributionPieChart data={typeBreakdown} />
          )}
        </div>

        <div className="ops-card p-3">
          <h2 className="mb-2 ops-section-title">Zone priority distribution</h2>
          {priorityBreakdown.length === 0 ? (
            <p className="ops-muted">No active zone priority data.</p>
          ) : (
            <DistributionPieChart data={priorityBreakdown} />
          )}
        </div>
      </div>

      <div className="ops-card p-3">
        <h2 className="mb-2 ops-section-title">Recent mission activity</h2>
        {recentMissions.length === 0 ? (
          <p className="ops-muted">No mission activity recorded.</p>
        ) : (
          <table className="ops-table w-full">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th className="py-1.5">Code</th>
                <th className="py-1.5">Zone</th>
                <th className="py-1.5">Priority</th>
                <th className="py-1.5">Status</th>
                <th className="py-1.5">Route</th>
              </tr>
            </thead>
            <tbody>
              {recentMissions.map((mission) => (
                <tr key={mission.id} className="border-b border-[var(--border)]">
                  <td className="py-1.5 font-mono">{mission.mission_code}</td>
                  <td className="py-1.5">{mission.zone_id}</td>
                  <td className="py-1.5">{mission.priority}</td>
                  <td className="py-1.5">{mission.status}</td>
                  <td className="py-1.5">{formatRouteDistanceKm(mission.route_distance_km)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
