import { useEffect, useMemo, useState } from "react"
import { getMissions, updateMissionStatus, assignMissionTeam } from "../api/missions"
import { getDashboardMetrics } from "../api/analytics"
import { getZones } from "../api/zones"
import { getReliefCenters } from "../api/inventory"
import { getFieldTeams } from "../api/fieldTeams"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { severityBadge, statusBadge } from "../utils/badgeUtils"
import { ErrorState } from "../components/ui/StateMessage"
import usePagination from "../hooks/usePagination"

const VALID_TRANSITIONS = {
  Created: "Allocated",
  Allocated: "Dispatched",
  Dispatched: "In Transit",
  "In Transit": "Delivered",
}

function nextStatus(current) {
  return VALID_TRANSITIONS[current] || null
}

export default function Missions() {
  const [missions, setMissions] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [zones, setZones] = useState([])
  const [depots, setDepots] = useState([])
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [actionError, setActionError] = useState("")
  const [assignSelection, setAssignSelection] = useState({})
  const [assigningId, setAssigningId] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([getMissions(), getDashboardMetrics(), getZones(), getReliefCenters(), getFieldTeams()])
      .then(([missionRows, dashboard, zoneRows, depotRows, teamRows]) => {
        if (cancelled) return
        setMissions(missionRows)
        setMetrics(dashboard)
        setZones(zoneRows)
        setDepots(depotRows)
        setTeams(teamRows)
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
    () => teams.filter((team) => team.status === "Available"),
    [teams],
  )

  async function refreshMissionData() {
    const [missionRows, teamRows] = await Promise.all([getMissions(), getFieldTeams()])
    setMissions(missionRows)
    setTeams(teamRows)
  }

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
  } = usePagination(missions, 10)

  async function advanceStatus(missionId, currentStatus) {
    const next = nextStatus(currentStatus)
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
    return !mission.field_team_id && ["Created", "Allocated"].includes(mission.status)
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Mission Operations" subtitle="Live mission lifecycle and dispatch status" />
        <p className="text-sm text-[var(--text-muted)]">Loading missions...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <PageHeader title="Mission Operations" subtitle="Live mission lifecycle and dispatch status" />
      {error && <ErrorState title="Unable to load missions" message={error} />}
      {actionError && <ErrorState title="Status update failed" message={actionError} />}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="ops-card p-2.5">
          <p className="text-sm text-[var(--text-muted)]">Total</p>
          <p className="text-xl font-bold">{metrics?.total_missions ?? missions.length}</p>
        </div>
        <div className="ops-card p-2.5">
          <p className="text-sm text-[var(--text-muted)]">Active</p>
          <p className="text-xl font-bold">{metrics?.active_missions ?? 0}</p>
        </div>
        <div className="ops-card p-2.5">
          <p className="text-sm text-[var(--text-muted)]">Delivered</p>
          <p className="text-xl font-bold">{metrics?.delivered_missions ?? 0}</p>
        </div>
        <div className="ops-card p-2.5">
          <p className="text-sm text-[var(--text-muted)]">Reserved Stock</p>
          <p className="text-xl font-bold">{metrics?.reserved_resources ?? 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <div className="ops-card p-3 xl:col-span-1">
          <h2 className="mb-2 text-sm font-semibold">Status Distribution</h2>
          {(metrics?.mission_status_distribution || []).length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">No mission status data yet.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {metrics.mission_status_distribution.map((row) => (
                <li key={row.status} className="flex justify-between border-b border-[var(--border)] py-1">
                  <span>{row.status}</span>
                  <strong>{row.count}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="ops-card overflow-hidden xl:col-span-3">
          <div className="border-b border-[var(--border)] px-3 py-2">
            <h2 className="text-sm font-semibold">Mission Table</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="ops-table min-w-full">
              <thead>
                <tr className="border-b border-[var(--border)] text-left">
                  <th className="px-3 py-2">Code</th>
                  <th className="px-3 py-2">Destination</th>
                  <th className="px-3 py-2">Team</th>
                  <th className="px-3 py-2">Depot</th>
                  <th className="px-3 py-2">Route</th>
                  <th className="px-3 py-2">Priority</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-3 py-6 text-center text-sm text-[var(--text-muted)]">
                      No missions yet. Create one from Allocation.
                    </td>
                  </tr>
                ) : (
                  pageItems.map((mission) => {
                    const next = nextStatus(mission.status)
                    return (
                      <tr key={mission.id} className="border-b border-[var(--border)]">
                        <td className="px-3 py-2 font-mono text-sm">{mission.mission_code}</td>
                        <td className="px-3 py-2">{zoneMap[mission.zone_id] || mission.zone_id}</td>
                        <td className="px-3 py-2">{teamMap[mission.field_team_id] || "—"}</td>
                        <td className="px-3 py-2">{depotMap[mission.relief_center_id] || "—"}</td>
                        <td className="px-3 py-2">{mission.route_distance_km != null ? `${mission.route_distance_km} km` : "—"}</td>
                        <td className="px-3 py-2">
                          <Badge variant={severityBadge(mission.priority)}>{mission.priority}</Badge>
                        </td>
                        <td className="px-3 py-2">
                          <Badge variant={statusBadge(mission.status)}>{mission.status}</Badge>
                        </td>
                        <td className="px-3 py-2">
                          {canAssignTeam(mission) ? (
                            <div className="flex min-w-[12rem] flex-col gap-1">
                              <Select
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
                                className="ops-btn ops-btn-primary"
                                disabled={!assignSelection[mission.id] || assigningId === mission.id}
                                onClick={() => assignTeam(mission.id)}
                              >
                                {assigningId === mission.id ? "Assigning..." : "Assign Team"}
                              </button>
                            </div>
                          ) : next ? (
                            <button
                              type="button"
                              className="ops-btn ops-btn-primary"
                              onClick={() => advanceStatus(mission.id, mission.status)}
                            >
                              → {next}
                            </button>
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
