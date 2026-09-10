import { useEffect, useMemo, useState } from "react"
import { getMissions, updateMissionStatus, assignMissionTeam } from "../api/missions"
import { getDashboardMetrics } from "../api/analytics"
import { getZones } from "../api/zones"
import { getReliefCenters } from "../api/inventory"
import { getFieldTeams } from "../api/fieldTeams"
import { getSystemMetadata } from "../api/system"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { severityBadge, statusBadge } from "../utils/badgeUtils"
import { formatRouteDistanceKm } from "../utils/routeUtils"
import { ErrorState } from "../components/ui/StateMessage"
import usePagination from "../hooks/usePagination"
import useResponsivePageSize from "../hooks/useResponsivePageSize"

export default function Missions() {
  const [missions, setMissions] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [zones, setZones] = useState([])
  const [depots, setDepots] = useState([])
  const [teams, setTeams] = useState([])
  const [workflow, setWorkflow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [actionError, setActionError] = useState("")
  const [assignSelection, setAssignSelection] = useState({})
  const [assigningId, setAssigningId] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      getMissions(),
      getDashboardMetrics(),
      getZones(),
      getReliefCenters(),
      getFieldTeams(),
      getSystemMetadata(),
    ])
      .then(([missionRows, dashboard, zoneRows, depotRows, teamRows, metadata]) => {
        if (cancelled) return
        setMissions(missionRows)
        setMetrics(dashboard)
        setZones(zoneRows)
        setDepots(depotRows)
        setTeams(teamRows)
        setWorkflow(metadata)
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

  const zoneMap = useMemo(() => Object.fromEntries(zones.map((z) => [z.id, z.zone_name])), [zones])
  const depotMap = useMemo(() => Object.fromEntries(depots.map((d) => [d.id, d.name])), [depots])
  const teamMap = useMemo(() => Object.fromEntries(teams.map((t) => [t.id, t.team_name])), [teams])
  const availableTeams = useMemo(
    () => teams.filter((team) => team.status === workflow?.available_field_team_status),
    [teams, workflow],
  )

  function allowedNextStatuses(currentStatus) {
    return workflow?.mission_transitions?.[currentStatus] || []
  }

  async function refreshMissionData() {
    const [missionRows, teamRows] = await Promise.all([getMissions(), getFieldTeams()])
    setMissions(missionRows)
    setTeams(teamRows)
  }

  const pageSize = useResponsivePageSize()
  const {
    page,
    pageItems,
    totalPages,
    totalItems,
    rangeStart,
    rangeEnd,
    goToPage,
    hasPrevious,
    hasNext,
  } = usePagination(missions, pageSize)

  async function advanceStatus(missionId, next) {
    if (!next) return
    setActionError("")
    try {
      await updateMissionStatus(missionId, next)
      await refreshMissionData()
    } catch (err) {
      setActionError(err.message)
    }
  }

  async function assignTeam(missionId) {
    const fieldTeamId = Number(assignSelection[missionId])
    if (!fieldTeamId) return
    setActionError("")
    setAssigningId(missionId)
    try {
      await assignMissionTeam(missionId, fieldTeamId)
      setAssignSelection((prev) => {
        const next = { ...prev }
        delete next[missionId]
        return next
      })
      await refreshMissionData()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setAssigningId(null)
    }
  }

  function canAssignTeam(mission) {
    const assignable = workflow?.assignable_mission_statuses || []
    return !mission.field_team_id && assignable.includes(mission.status)
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Mission Operations" subtitle="Live mission lifecycle and dispatch status" />
        <p className="ops-muted">Loading missions...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <PageHeader title="Mission Operations" subtitle="Live mission lifecycle and dispatch status" />
      {error && <ErrorState title="Unable to load missions" message={error} />}
      {actionError && <ErrorState title="Status update failed" message={actionError} />}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="ops-card px-3 py-2">
          <p className="ops-section-label">Total</p>
          <p className="text-lg font-semibold tabular-nums">{metrics?.total_missions ?? missions.length}</p>
        </div>
        <div className="ops-card px-3 py-2">
          <p className="ops-section-label">Active</p>
          <p className="text-lg font-semibold tabular-nums">{metrics?.active_missions ?? 0}</p>
        </div>
        <div className="ops-card px-3 py-2">
          <p className="ops-section-label">Delivered</p>
          <p className="text-lg font-semibold tabular-nums">{metrics?.delivered_missions ?? 0}</p>
        </div>
        <div className="ops-card px-3 py-2">
          <p className="ops-section-label">Reserved Stock</p>
          <p className="text-lg font-semibold tabular-nums">{metrics?.reserved_resources ?? 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <div className="ops-card p-3 xl:col-span-1">
          <h2 className="mb-2 ops-section-title">Status Distribution</h2>
          {(metrics?.mission_status_distribution || []).length === 0 ? (
            <p className="ops-muted">No mission status data yet.</p>
          ) : (
            <ul>
              {metrics.mission_status_distribution.map((row) => (
                <li key={row.status} className="flex justify-between border-b border-[var(--border)] py-1 last:border-0">
                  <span>{row.status}</span>
                  <strong>{row.count}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="ops-card overflow-hidden xl:col-span-3">
          <div className="border-b border-[var(--border)] px-3 py-2">
            <h2 className="ops-section-title">Mission Table</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="ops-table min-w-full">
              <thead>
                <tr className="border-b border-[var(--border)] text-left">
                  <th >Code</th>
                  <th >Destination</th>
                  <th >Team</th>
                  <th >Depot</th>
                  <th >Route</th>
                  <th >Priority</th>
                  <th >Status</th>
                  <th >Action</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-3 py-6 text-center ops-muted">
                      No missions yet. Create one from Allocation.
                    </td>
                  </tr>
                ) : (
                  pageItems.map((mission) => {
                    const nextStatuses = allowedNextStatuses(mission.status)
                    return (
                      <tr key={mission.id} className="border-b border-[var(--border)]">
                        <td className="font-mono">{mission.mission_code}</td>
                        <td >{zoneMap[mission.zone_id] || mission.zone_id}</td>
                        <td >{teamMap[mission.field_team_id] || "—"}</td>
                        <td >{depotMap[mission.relief_center_id] || "—"}</td>
                        <td >{formatRouteDistanceKm(mission.route_distance_km)}</td>
                        <td >
                          <Badge variant={severityBadge(mission.priority)}>{mission.priority}</Badge>
                        </td>
                        <td >
                          <Badge variant={statusBadge(mission.status)}>{mission.status}</Badge>
                        </td>
                        <td>
                          {canAssignTeam(mission) ? (
                            <div className="flex min-w-[10rem] items-center gap-1">
                              <Select
                                className="min-w-0"
                                value={assignSelection[mission.id] || ""}
                                onChange={(e) =>
                                  setAssignSelection((prev) => ({
                                    ...prev,
                                    [mission.id]: e.target.value,
                                  }))
                                }
                              >
                                <option value="">Select team...</option>
                                {availableTeams.map((team) => (
                                  <option key={team.id} value={team.id}>
                                    {team.team_name}
                                  </option>
                                ))}
                              </Select>
                              <button
                                type="button"
                                className="ops-btn ops-btn-primary shrink-0 px-2 py-1"
                                disabled={!assignSelection[mission.id] || assigningId === mission.id}
                                onClick={() => assignTeam(mission.id)}
                              >
                                {assigningId === mission.id ? "…" : "Assign"}
                              </button>
                            </div>
                          ) : nextStatuses.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {nextStatuses.map((next) => (
                                <button
                                  key={next}
                                  type="button"
                                  className="ops-btn ops-btn-primary px-2 py-1"
                                  onClick={() => advanceStatus(mission.id, next)}
                                >
                                  → {next}
                                </button>
                              ))}
                            </div>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            totalItems={totalItems}
            rangeStart={rangeStart}
            rangeEnd={rangeEnd}
            onPageChange={goToPage}
            hasPrevious={hasPrevious}
            hasNext={hasNext}
          />
        </div>
      </div>
    </div>
  )
}
