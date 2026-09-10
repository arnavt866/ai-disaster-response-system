import { useCallback, useEffect, useMemo, useState } from "react"

import { Link } from "react-router-dom"

import {

  createFieldTeam,

  deactivateFieldTeam,

  getFieldTeams,

  updateFieldTeam,

} from "../api/fieldTeams"

import { getMissions } from "../api/missions"

import { getZones } from "../api/zones"

import { getSystemMetadata } from "../api/system"

import PageHeader from "../components/ui/PageHeader"

import Select from "../components/ui/Select"

import SearchInput from "../components/ui/SearchInput"

import Pagination from "../components/ui/Pagination"

import Badge from "../components/ui/Badge"

import { statusBadge } from "../utils/badgeUtils"

import { ErrorState } from "../components/ui/StateMessage"

import usePagination from "../hooks/usePagination"
import useResponsivePageSize from "../hooks/useResponsivePageSize"

const EMPTY_TEAM_FORM = {

  team_name: "",

  vehicle_type: "",

  vehicle_capacity: "0",

  personnel_count: "",

  contact_number: "",

  base_latitude: "",

  base_longitude: "",

  status: "Available",

}



function teamToForm(team) {

  return {

    team_name: team.team_name || "",

    vehicle_type: team.vehicle_type || "",

    vehicle_capacity: String(team.vehicle_capacity ?? 0),

    personnel_count: team.personnel_count != null ? String(team.personnel_count) : "",

    contact_number: team.contact_number || "",

    base_latitude: team.base_latitude != null ? String(team.base_latitude) : "",

    base_longitude: team.base_longitude != null ? String(team.base_longitude) : "",

    status: team.status || "Available",

  }

}



function parseOptionalNumber(value) {

  const trimmed = String(value ?? "").trim()

  if (!trimmed) return null

  const parsed = Number(trimmed)

  return Number.isFinite(parsed) ? parsed : null

}



function buildTeamPayload(form, { includeStatus = false } = {}) {

  const payload = {

    team_name: form.team_name.trim(),

    vehicle_type: form.vehicle_type.trim() || null,

    vehicle_capacity: Math.max(0, Number(form.vehicle_capacity) || 0),

    personnel_count: parseOptionalNumber(form.personnel_count),

    contact_number: form.contact_number.trim() || null,

    base_latitude: parseOptionalNumber(form.base_latitude),

    base_longitude: parseOptionalNumber(form.base_longitude),

  }

  if (includeStatus) {

    payload.status = form.status

  }

  return payload

}



function TeamFormFields({ form, setForm, statusOptions, showStatus = false }) {

  return (

    <div className="space-y-2">

      <label className="block">

        <span className="text-[var(--text-muted)]">Team name</span>

        <input

          className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"

          value={form.team_name}

          onChange={(e) => setForm((prev) => ({ ...prev, team_name: e.target.value }))}

          required

        />

      </label>

      <label className="block">

        <span className="text-[var(--text-muted)]">Vehicle type</span>

        <input

          className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"

          value={form.vehicle_type}

          onChange={(e) => setForm((prev) => ({ ...prev, vehicle_type: e.target.value }))}

        />

      </label>

      <div className="grid grid-cols-2 gap-2">

        <label className="block">

          <span className="text-[var(--text-muted)]">Vehicle capacity</span>

          <input

            type="number"

            min="0"

            className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"

            value={form.vehicle_capacity}

            onChange={(e) => setForm((prev) => ({ ...prev, vehicle_capacity: e.target.value }))}

          />

        </label>

        <label className="block">

          <span className="text-[var(--text-muted)]">Personnel count</span>

          <input

            type="number"

            min="0"

            className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"

            value={form.personnel_count}

            onChange={(e) => setForm((prev) => ({ ...prev, personnel_count: e.target.value }))}

          />

        </label>

      </div>

      <label className="block">

        <span className="text-[var(--text-muted)]">Contact number</span>

        <input

          className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"

          value={form.contact_number}

          onChange={(e) => setForm((prev) => ({ ...prev, contact_number: e.target.value }))}

        />

      </label>

      <div className="grid grid-cols-2 gap-2">

        <label className="block">

          <span className="text-[var(--text-muted)]">Base latitude</span>

          <input

            className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"

            value={form.base_latitude}

            onChange={(e) => setForm((prev) => ({ ...prev, base_latitude: e.target.value }))}

          />

        </label>

        <label className="block">

          <span className="text-[var(--text-muted)]">Base longitude</span>

          <input

            className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"

            value={form.base_longitude}

            onChange={(e) => setForm((prev) => ({ ...prev, base_longitude: e.target.value }))}

          />

        </label>

      </div>

      {showStatus && (

        <label className="block">

          <span className="text-[var(--text-muted)]">Status</span>

          <Select

            className="mt-1 w-full"

            value={form.status}

            onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value }))}

          >

            {statusOptions.map((status) => (

              <option key={status} value={status}>{status}</option>

            ))}

          </Select>

        </label>

      )}

    </div>

  )

}



export default function Teams() {

  const [teams, setTeams] = useState([])

  const [missions, setMissions] = useState([])

  const [zones, setZones] = useState([])

  const [activeMissionStatuses, setActiveMissionStatuses] = useState([])

  const [inactiveTeamStatus, setInactiveTeamStatus] = useState("Inactive")

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState("")

  const [actionError, setActionError] = useState("")

  const [actionNotice, setActionNotice] = useState("")

  const [searchTerm, setSearchTerm] = useState("")

  const [statusFilter, setStatusFilter] = useState("All")

  const [showInactive, setShowInactive] = useState(false)

  const [selectedTeamId, setSelectedTeamId] = useState(null)

  const [showCreateForm, setShowCreateForm] = useState(false)

  const [createForm, setCreateForm] = useState(EMPTY_TEAM_FORM)

  const [createSaving, setCreateSaving] = useState(false)

  const [editMode, setEditMode] = useState(false)

  const [editForm, setEditForm] = useState(EMPTY_TEAM_FORM)

  const [editSaving, setEditSaving] = useState(false)

  const [deactivating, setDeactivating] = useState(false)



  const loadTeams = useCallback(async () => {

    const teamRows = await getFieldTeams()

    setTeams(teamRows)

    return teamRows

  }, [])



  useEffect(() => {

    let cancelled = false

    Promise.all([getFieldTeams(), getMissions(), getZones(), getSystemMetadata()])

      .then(([teamRows, missionRows, zoneRows, metadata]) => {

        if (cancelled) return

        setTeams(teamRows)

        setMissions(missionRows)

        setZones(zoneRows)

        setActiveMissionStatuses(metadata.active_mission_statuses || [])

        setInactiveTeamStatus(metadata.inactive_field_team_status || "Inactive")

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
    const activeStatuses = new Set(activeMissionStatuses)
    const byTeam = new Map()

    missions.forEach((mission) => {
      if (!mission.field_team_id) return
      const list = byTeam.get(mission.field_team_id) || []
      list.push(mission)
      byTeam.set(mission.field_team_id, list)
    })

    const map = {}
    byTeam.forEach((list, teamId) => {
      const active = list.filter((mission) => activeStatuses.has(mission.status))
      const pool = active.length ? active : list
      map[teamId] = pool.sort((a, b) => b.id - a.id)[0]
    })
    return map
  }, [missions, activeMissionStatuses])

  function assignedMissionLabel(mission) {
    if (!mission) return "—"
    if (activeMissionStatuses.includes(mission.status)) return mission.mission_code
    return `${mission.mission_code} (${mission.status})`
  }



  const statusOptions = useMemo(

    () => ["All", ...new Set(teams.map((team) => team.status).filter(Boolean))],

    [teams],

  )



  const editableStatusOptions = useMemo(

    () => [...new Set(teams.map((team) => team.status).filter(Boolean))].filter(

      (status) => status !== inactiveTeamStatus,

    ),

    [teams, inactiveTeamStatus],

  )



  const activeTeamCount = useMemo(

    () => teams.filter((team) => team.status !== inactiveTeamStatus).length,

    [teams, inactiveTeamStatus],

  )



  const filtered = useMemo(() => {

    const search = searchTerm.trim().toLowerCase()

    return teams.filter((team) => {

      if (!showInactive && team.status === inactiveTeamStatus) {

        return false

      }



      const matchesSearch =

        !search ||

        team.team_name?.toLowerCase().includes(search) ||

        team.vehicle_type?.toLowerCase().includes(search)



      const matchesStatus = statusFilter === "All" || team.status === statusFilter

      return matchesSearch && matchesStatus

    })

  }, [teams, searchTerm, statusFilter, showInactive, inactiveTeamStatus])



  const pageSize = useResponsivePageSize()
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
  } = usePagination(filtered, pageSize)



  const displayedTeam =

    pageItems.find((team) => team.id === selectedTeamId) ?? pageItems[0] ?? null



  const displayedMission = displayedTeam ? missionByTeamId[displayedTeam.id] : null



  useEffect(() => {

    if (!displayedTeam) {

      setEditMode(false)

      return

    }

    setEditForm(teamToForm(displayedTeam))

  }, [displayedTeam])



  async function handleCreateTeam(event) {

    event.preventDefault()

    if (!createForm.team_name.trim()) {

      setActionError("Team name is required.")

      return

    }



    setCreateSaving(true)

    setActionError("")

    setActionNotice("")

    try {

      const created = await createFieldTeam(buildTeamPayload(createForm))

      const teamRows = await loadTeams()

      setSelectedTeamId(created.id)

      setCreateForm(EMPTY_TEAM_FORM)

      setShowCreateForm(false)

      setActionNotice(`Created team "${created.team_name}".`)

      if (!teamRows.some((team) => team.id === created.id && team.status !== inactiveTeamStatus)) {

        setShowInactive(true)

      }

    } catch (err) {

      setActionError(err.message)

    } finally {

      setCreateSaving(false)

    }

  }



  async function handleSaveEdit(event) {

    event.preventDefault()

    if (!displayedTeam) return

    if (!editForm.team_name.trim()) {

      setActionError("Team name is required.")

      return

    }



    setEditSaving(true)

    setActionError("")

    setActionNotice("")

    try {

      const updated = await updateFieldTeam(

        displayedTeam.id,

        buildTeamPayload(editForm, { includeStatus: true }),

      )

      await loadTeams()

      setSelectedTeamId(updated.id)

      setEditMode(false)

      setActionNotice(`Updated team "${updated.team_name}".`)

    } catch (err) {

      setActionError(err.message)

    } finally {

      setEditSaving(false)

    }

  }



  async function handleDeactivateTeam() {

    if (!displayedTeam) return

    const confirmed = window.confirm(

      `Deactivate "${displayedTeam.team_name}"? The team will be marked Inactive and hidden from active roster views.`,

    )

    if (!confirmed) return



    setDeactivating(true)

    setActionError("")

    setActionNotice("")

    try {

      await deactivateFieldTeam(displayedTeam.id)

      await loadTeams()

      setSelectedTeamId(null)

      setEditMode(false)

      setActionNotice(`Deactivated team "${displayedTeam.team_name}".`)

    } catch (err) {

      setActionError(err.message)

    } finally {

      setDeactivating(false)

    }

  }



  if (loading) {

    return (

      <div className="space-y-3">

        <PageHeader title="Field Teams" subtitle="Response crews and vehicle capacity" />

        <p className="ops-muted">Loading field teams...</p>

      </div>

    )

  }



  return (

    <div className="space-y-3">

      <PageHeader

        title="Field Teams"

        subtitle={`${activeTeamCount} active crews — vehicles and personnel (DB-backed CRUD)`}

        actions={(

          <button

            type="button"

            className="ops-btn ops-btn-primary"

            onClick={() => {

              setShowCreateForm((open) => !open)

              setActionError("")

            }}

          >

            {showCreateForm ? "Close form" : "Add team"}

          </button>

        )}

      />

      {error && <ErrorState title="Unable to load field teams" message={error} />}

      {actionError && <ErrorState title="Team action failed" message={actionError} />}

      {actionNotice && (

        <p className="rounded-md border border-[var(--success)] px-3 py-2 text-[var(--success)]">

          {actionNotice}

        </p>

      )}



      {showCreateForm && (

        <form className="ops-card space-y-3 p-3" onSubmit={handleCreateTeam}>

          <h2 className="ops-section-title">Register new field team</h2>

          <TeamFormFields form={createForm} setForm={setCreateForm} statusOptions={editableStatusOptions} />

          <div className="flex gap-2">

            <button type="submit" className="ops-btn ops-btn-primary" disabled={createSaving}>

              {createSaving ? "Creating..." : "Create team"}

            </button>

            <button

              type="button"

              className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)]"

              onClick={() => setCreateForm(EMPTY_TEAM_FORM)}

            >

              Reset

            </button>

          </div>

        </form>

      )}



      <div className="ops-card p-3">

        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">

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

          <label className="flex items-center gap-2 ops-muted">

            <input

              type="checkbox"

              checked={showInactive}

              onChange={(e) => {

                setShowInactive(e.target.checked)

                resetPage()

              }}

            />

            Show inactive teams

          </label>

        </div>

      </div>



      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">

        <div className="ops-card overflow-hidden xl:col-span-3">

          <div className="border-b border-[var(--border)] px-3 py-2">

            <h2 className="ops-section-title">Field Team Roster</h2>

          </div>

          <div className="overflow-x-auto">

            <table className="ops-table min-w-full">

              <thead>

                <tr className="border-b border-[var(--border)] text-left">

                  <th >Team</th>

                  <th >Status</th>

                  <th >Vehicle</th>

                  <th >Personnel</th>

                  <th >Capacity</th>

                  <th >Assigned Mission</th>

                  <th >Destination Zone</th>

                </tr>

              </thead>

              <tbody>

                {pageItems.length === 0 ? (

                  <tr>

                    <td colSpan={7} className="px-3 py-6 text-center ops-muted">

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

                        onClick={() => {

                          setSelectedTeamId(team.id)

                          setEditMode(false)

                        }}

                      >

                        <td className="font-medium">{team.team_name}</td>

                        <td >

                          <Badge variant={statusBadge(team.status)}>{team.status}</Badge>

                        </td>

                        <td >{team.vehicle_type || "—"}</td>

                        <td >

                          {team.personnel_count != null ? team.personnel_count.toLocaleString() : "—"}

                        </td>

                        <td >

                          {team.vehicle_capacity ? team.vehicle_capacity.toLocaleString() : "—"}

                        </td>

                        <td className="font-mono">

                          {assignedMissionLabel(mission)}

                        </td>

                        <td >

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

          <div className="mb-2 flex items-center justify-between gap-2">

            <h2 className="ops-section-title">Team Detail</h2>

            {displayedTeam && displayedTeam.status !== inactiveTeamStatus && !editMode && (

              <div className="flex gap-1">

                <button

                  type="button"

                  className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)]"

                  onClick={() => setEditMode(true)}

                >

                  Edit

                </button>

                <button

                  type="button"

                  className="ops-btn bg-[var(--critical)] text-white"

                  onClick={handleDeactivateTeam}

                  disabled={deactivating}

                >

                  {deactivating ? "..." : "Deactivate"}

                </button>

              </div>

            )}

          </div>

          {!displayedTeam ? (

            <p className="ops-muted">Select a team to view details.</p>

          ) : editMode ? (

            <form className="space-y-3" onSubmit={handleSaveEdit}>

              <TeamFormFields

                form={editForm}

                setForm={setEditForm}

                statusOptions={editableStatusOptions.length ? editableStatusOptions : [editForm.status]}

                showStatus

              />

              <div className="flex gap-2">

                <button type="submit" className="ops-btn ops-btn-primary" disabled={editSaving}>

                  {editSaving ? "Saving..." : "Save changes"}

                </button>

                <button

                  type="button"

                  className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)]"

                  onClick={() => {

                    setEditMode(false)

                    setEditForm(teamToForm(displayedTeam))

                  }}

                >

                  Cancel

                </button>

              </div>

            </form>

          ) : (

            <dl className="space-y-2">

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

                <dt className="text-[var(--text-muted)]">Personnel</dt>

                <dd>{displayedTeam.personnel_count?.toLocaleString() ?? "—"}</dd>

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

                <dd className="text-[var(--text-secondary)]">

                  {displayedTeam.base_latitude != null && displayedTeam.base_longitude != null

                    ? `${displayedTeam.base_latitude.toFixed(4)}, ${displayedTeam.base_longitude.toFixed(4)}`

                    : "—"}

                </dd>

              </div>

              <div>

                <dt className="text-[var(--text-muted)]">Assigned Mission</dt>

                <dd>{assignedMissionLabel(displayedMission)}</dd>

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


