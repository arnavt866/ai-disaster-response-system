import { useEffect, useMemo, useState } from "react"
import { getDisasters } from "../api/disasters"
import { getDashboardMetrics } from "../api/analytics"
import { getMissions } from "../api/missions"
import PageHeader from "../components/ui/PageHeader"
import IncidentLineChart from "../components/Charts/IncidentLineChart"
import DistributionPieChart from "../components/Charts/DistributionPieChart"
import { ErrorState } from "../components/ui/StateMessage"
import { formatDisasterType } from "../utils/disasterHelpers"

function formatDateKey(eventTime) {
  if (!eventTime) return "Unknown"
  const date = new Date(eventTime)
  if (Number.isNaN(date.getTime())) return "Unknown"
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
}

export default function Reports() {
  const [disasters, setDisasters] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    Promise.all([getDisasters(), getDashboardMetrics(), getMissions()])
      .then(([events, dashboard, missionRows]) => {
        if (!cancelled) {
          setDisasters(events)
          setMetrics(dashboard)
          setMissions(missionRows)
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

  if (loading) {
    return (
      <div className="space-y-2">
        <PageHeader title="Operational Reports" subtitle="Analytics and incident summaries from live backend data" />
        <p className="text-sm text-[var(--text-muted)]">Loading reports...</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <PageHeader title="Operational Reports" subtitle="Analytics and incident summaries from live backend data" />
      {error && <ErrorState title="Unable to load reports" message={error} />}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="ops-card p-2">
          <p className="text-sm text-[var(--text-muted)]">Incidents</p>
          <p className="text-xl font-bold">{disasters.length}</p>
        </div>
        <div className="ops-card p-2">
          <p className="text-sm text-[var(--text-muted)]">Active Zones</p>
          <p className="text-xl font-bold">{metrics?.active_zones ?? 0}</p>
        </div>
        <div className="ops-card p-2">
          <p className="text-sm text-[var(--text-muted)]">Allocated Units</p>
          <p className="text-xl font-bold">{metrics?.allocated_resources ?? 0}</p>
        </div>
        <div className="ops-card p-2">
          <p className="text-sm text-[var(--text-muted)]">Unmet Demand</p>
          <p className="text-xl font-bold">{metrics?.unmet_demand ?? 0}</p>
        </div>
      </div>

      <div className="ops-card p-2">
        <h2 className="mb-2 text-sm font-semibold">Incidents Over Time</h2>
        <IncidentLineChart data={incidentsOverTime} />
      </div>

      <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
        <div className="ops-card p-2">
          <h2 className="mb-2 text-sm font-semibold">Incident Type Breakdown</h2>
          {typeBreakdown.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">No disaster events recorded.</p>
          ) : (
            <DistributionPieChart data={typeBreakdown} />
          )}
        </div>

        <div className="ops-card p-2">
          <h2 className="mb-2 text-sm font-semibold">Zone Priority Distribution</h2>
          {priorityBreakdown.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">No active zone priority data.</p>
          ) : (
            <DistributionPieChart data={priorityBreakdown} />
          )}
        </div>
      </div>

      <div className="ops-card p-2">
        <h2 className="mb-2 text-sm font-semibold">Recent Mission Activity</h2>
        {recentMissions.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)]">No mission activity recorded.</p>
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
                  <td className="py-1.5 font-mono text-sm">{mission.mission_code}</td>
                  <td className="py-1.5">{mission.zone_id}</td>
                  <td className="py-1.5">{mission.priority}</td>
                  <td className="py-1.5">{mission.status}</td>
                  <td className="py-1.5">{mission.route_distance_km != null ? `${mission.route_distance_km} km` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
