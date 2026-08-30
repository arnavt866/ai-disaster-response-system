import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { getFieldTeams } from "../api/fieldTeams"
import { getMissions } from "../api/missions"
import { getZones } from "../api/zones"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import SearchInput from "../components/ui/SearchInput"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { statusBadge } from "../utils/badgeUtils"
import { ErrorState } from "../components/ui/StateMessage"
import usePagination from "../hooks/usePagination"

const PAGE_SIZE = 15

export default function Teams() {
  const [teams, setTeams] = useState([])
  const [missions, setMissions] = useState([])
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("All")
  const [selectedTeamId, setSelectedTeamId] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([getFieldTeams(), getMissions(), getZones()])
      .then(([teamRows, missionRows, zoneRows]) => {
        if (cancelled) return
        setTeams(teamRows)
        setMissions(missionRows)
        setZones(zoneRows)
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

  const zoneMap = useMemo(
    () => Object.fromEntries(zones.map((zone) => [zone.id, zone.zone_name])),
    [zones],
  )

  const missionByTeamId = useMemo(() => {
    const activeStatuses = new Set(["Allocated", "Dispatched", "In Transit"])
    const map = {}
    missions.forEach((mission) => {
      if (mission.field_team_id && activeStatuses.has(mission.status)) {
        map[mission.field_team_id] = mission
      }
    })
    return map
  }, [missions])

  const statusOptions = useMemo(
    () => ["All", ...new Set(teams.map((team) => team.status).filter(Boolean))],
    [teams],
  )

  const filtered = useMemo(() => {
    const search = searchTerm.trim().toLowerCase()
    return teams.filter((team) => {
      const matchesSearch =
        !search ||
        team.team_name?.toLowerCase().includes(search) ||
        team.vehicle_type?.toLowerCase().includes(search)

      const matchesStatus = statusFilter === "All" || team.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [teams, searchTerm, statusFilter])

  const {
    page,
    pageItems,
    totalPages,
    totalItems,
    rangeStart,
    rangeEnd,
    goToPage,
    resetPage,
    hasPrevious,
    hasNext,
  } = usePagination(filtered, PAGE_SIZE)

  const displayedTeam =
    pageItems.find((team) => team.id === selectedTeamId) ?? pageItems[0] ?? null

  const displayedMission = displayedTeam ? missionByTeamId[displayedTeam.id] : null

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Field Teams" subtitle="Response crews and vehicle capacity" />
        <p className="text-sm text-[var(--text-muted)]">Loading field teams...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <PageHeader
        title="Field Teams"
        subtitle={`${teams.length} crews registered in the field team service`}
      />
      {error && <ErrorState title="Unable to load field teams" message={error} />}

      <div className="ops-card p-3">
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <SearchInput
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              resetPage()
            }}
            placeholder="Search team name or vehicle..."
          />
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              resetPage()
            }}
          >
            <option value="All">All Statuses</option>
            {statusOptions.filter((value) => value !== "All").map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <div className="ops-card overflow-hidden xl:col-span-3">
          <div className="border-b border-[var(--border)] px-3 py-2">
            <h2 className="text-sm font-semibold">Field Team Roster</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="ops-table min-w-full">
              <thead>
                <tr className="border-b border-[var(--border)] text-left">
                  <th className="px-3 py-2">Team</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Vehicle</th>
                  <th className="px-3 py-2">Capacity</th>
                  <th className="px-3 py-2">Assigned Mission</th>
                  <th className="px-3 py-2">Destination Zone</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-sm text-[var(--text-muted)]">
                      No field teams found.
                    </td>
                  </tr>
                ) : (
                  pageItems.map((team) => {
                    const mission = missionByTeamId[team.id]
                    return (
                      <tr
                        key={team.id}
                        className={`cursor-pointer border-b border-[var(--border)] ${
                          displayedTeam?.id === team.id ? "ops-row-selected" : ""
                        }`}
                        onClick={() => setSelectedTeamId(team.id)}
                      >
                        <td className="px-3 py-2 font-medium">{team.team_name}</td>
                        <td className="px-3 py-2">
                          <Badge variant={statusBadge(team.status)}>{team.status}</Badge>
                        </td>
                        <td className="px-3 py-2">{team.vehicle_type || "—"}</td>
                        <td className="px-3 py-2">
                          {team.vehicle_capacity ? team.vehicle_capacity.toLocaleString() : "—"}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs">
                          {mission?.mission_code || "—"}
                        </td>
                        <td className="px-3 py-2">
                          {mission ? zoneMap[mission.zone_id] || mission.zone_id : "—"}
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

        <div className="ops-card p-3">
          <h2 className="mb-2 text-sm font-semibold">Team Detail</h2>
          {!displayedTeam ? (
            <p className="text-sm text-[var(--text-muted)]">Select a team to view details.</p>
          ) : (
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-[var(--text-muted)]">Team Name</dt>
                <dd className="font-medium">{displayedTeam.team_name}</dd>
              </div>
              <div>
                <dt className="text-[var(--text-muted)]">Status</dt>
                <dd>
                  <Badge variant={statusBadge(displayedTeam.status)}>{displayedTeam.status}</Badge>
                </dd>
              </div>
              <div>
                <dt className="text-[var(--text-muted)]">Vehicle</dt>
                <dd>{displayedTeam.vehicle_type || "—"}</dd>
              </div>
              <div>
                <dt className="text-[var(--text-muted)]">Capacity</dt>
                <dd>{displayedTeam.vehicle_capacity?.toLocaleString() ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-[var(--text-muted)]">Contact</dt>
                <dd>{displayedTeam.contact_number || "—"}</dd>
              </div>
              <div>
                <dt className="text-[var(--text-muted)]">Base Location</dt>
                <dd className="text-xs text-[var(--text-secondary)]">
                  {displayedTeam.base_latitude != null && displayedTeam.base_longitude != null
                    ? `${displayedTeam.base_latitude.toFixed(4)}, ${displayedTeam.base_longitude.toFixed(4)}`
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-[var(--text-muted)]">Assigned Mission</dt>
                <dd>{displayedMission?.mission_code || "—"}</dd>
              </div>
              <div>
                <dt className="text-[var(--text-muted)]">Destination Zone</dt>
                <dd>
                  {displayedMission ? (
                    <Link
                      to="/zones"
                      className="font-medium text-[var(--primary)] hover:underline"
                    >
                      {zoneMap[displayedMission.zone_id] || displayedMission.zone_id}
                    </Link>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
              {displayedMission && (
                <div>
                  <dt className="text-[var(--text-muted)]">Mission Status</dt>
                  <dd>
                    <Badge variant={statusBadge(displayedMission.status)}>
                      {displayedMission.status}
                    </Badge>
                  </dd>
                </div>
              )}
            </dl>
          )}
        </div>
      </div>
    </div>
  )
}
