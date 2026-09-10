import { useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { getZones } from "../api/zones"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import SearchInput from "../components/ui/SearchInput"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { severityBadge } from "../utils/badgeUtils"
import { ErrorState } from "../components/ui/StateMessage"
import InfoTooltip from "../components/ui/InfoTooltip"
import { computeZoneVulnerabilityFactor } from "../utils/vulnerabilityHelpers"
import usePagination from "../hooks/usePagination"
import useResponsivePageSize from "../hooks/useResponsivePageSize"

export default function Zones() {
  const [searchParams] = useSearchParams()
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("All")
  const [severityFilter, setSeverityFilter] = useState("All")
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get("priority") || "All")
  const [selectedZoneId, setSelectedZoneId] = useState(null)

  const urlPriority = searchParams.get("priority")
  const activePriorityFilter = urlPriority || priorityFilter

  useEffect(() => {
    let cancelled = false
    getZones()
      .then((data) => {
        if (!cancelled) setZones(data)
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

  const severityOptions = useMemo(
    () => ["All", ...new Set(zones.map((z) => z.severity).filter(Boolean))],
    [zones],
  )

  const statusOptions = useMemo(
    () => ["All", ...new Set(zones.map((z) => z.status).filter(Boolean))],
    [zones],
  )

  const priorityOptions = useMemo(
    () => ["All", ...new Set(zones.map((z) => z.operational_priority || z.severity).filter(Boolean))],
    [zones],
  )

  const filtered = useMemo(() => {
    const search = searchTerm.trim().toLowerCase()
    return zones.filter((zone) => {
      const matchesSearch =
        !search ||
        zone.zone_name?.toLowerCase().includes(search) ||
        zone.disaster_type?.toLowerCase().includes(search)

      const matchesStatus = statusFilter === "All" || zone.status === statusFilter
      const matchesSeverity = severityFilter === "All" || zone.severity === severityFilter
      const priority = zone.operational_priority || zone.severity
      const matchesPriority = activePriorityFilter === "All" || priority === activePriorityFilter

      return matchesSearch && matchesStatus && matchesSeverity && matchesPriority
    })
  }, [zones, searchTerm, statusFilter, severityFilter, activePriorityFilter])

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

  const displayedZone =
    pageItems.find((zone) => zone.id === selectedZoneId) ?? pageItems[0] ?? null

  const displayedVulnerability = displayedZone
    ? computeZoneVulnerabilityFactor(displayedZone)
    : null

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Disaster Zones" subtitle="Active zones from backend disaster zone service" />
        <p className="ops-muted">Loading zones...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <PageHeader title="Disaster Zones" subtitle="Active zones from backend disaster zone service" />
      {error && <ErrorState title="Unable to load zones" message={error} />}

      <div className="ops-card p-3">
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
          <SearchInput
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); resetPage() }}
            placeholder="Search zone name or type..."
          />
          <Select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); resetPage() }}>
            <option value="All">All Statuses</option>
            {statusOptions.filter((v) => v !== "All").map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </Select>
          <Select value={severityFilter} onChange={(e) => { setSeverityFilter(e.target.value); resetPage() }}>
            <option value="All">All Severities</option>
            {severityOptions.filter((v) => v !== "All").map((severity) => (
              <option key={severity} value={severity}>{severity}</option>
            ))}
          </Select>
          <Select value={priorityFilter} onChange={(e) => { setPriorityFilter(e.target.value); resetPage() }}>
            <option value="All">All Priorities</option>
            {priorityOptions.filter((v) => v !== "All").map((priority) => (
              <option key={priority} value={priority}>{priority}</option>
            ))}
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <div className="ops-card overflow-hidden xl:col-span-3">
          <div className="overflow-x-auto">
            <table className="ops-table min-w-full">
              <thead>
                <tr className="border-b border-[var(--border)] text-left">
                  <th >Zone</th>
                  <th >Type</th>
                  <th >Severity</th>
                  <th >Priority</th>
                  <th >Population</th>
                  <th >Status</th>
                  <th >Action</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-3 py-6 text-center ops-muted">
                      No zones found.
                    </td>
                  </tr>
                ) : (
                  pageItems.map((zone) => (
                    <tr
                      key={zone.id}
                      className={`cursor-pointer border-b border-[var(--border)] ${
                        displayedZone?.id === zone.id ? "ops-row-selected" : ""
                      }`}
                      onClick={() => setSelectedZoneId(zone.id)}
                    >
                      <td className="font-medium">{zone.zone_name}</td>
                      <td >{zone.disaster_type}</td>
                      <td >
                        <Badge variant={severityBadge(zone.severity)}>{zone.severity}</Badge>
                      </td>
                      <td >
                        <Badge variant={severityBadge(zone.operational_priority || zone.severity)}>
                          {zone.operational_priority || zone.severity}
                        </Badge>
                      </td>
                      <td >{zone.affected_population?.toLocaleString() ?? "—"}</td>
                      <td >{zone.status}</td>
                      <td >
                        <Link
                          to={`/dashboard?lat=${zone.latitude}&lon=${zone.longitude}&zoom=10`}
                          className="font-medium text-[var(--primary)] hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          View on map
                        </Link>
                      </td>
                    </tr>
                  ))
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
          <h2 className="mb-2 ops-section-title">Zone Detail</h2>
          {!displayedZone ? (
            <p className="ops-muted">Select a zone to view details.</p>
          ) : (
            <dl className="space-y-2">
              <div><dt className="text-[var(--text-muted)]">Zone ID</dt><dd className="font-medium">{displayedZone.zone_name}</dd></div>
              <div><dt className="text-[var(--text-muted)]">Type</dt><dd>{displayedZone.disaster_type}</dd></div>
              <div><dt className="text-[var(--text-muted)]">Severity</dt><dd>{displayedZone.severity}</dd></div>
              <div><dt className="text-[var(--text-muted)]">Priority</dt><dd>{displayedZone.operational_priority || displayedZone.severity}</dd></div>
              <div><dt className="text-[var(--text-muted)]">Population</dt><dd>{displayedZone.affected_population?.toLocaleString() ?? "—"}</dd></div>
              <div>
                <dt className="inline-flex items-center text-[var(--text-muted)]">
                  Vulnerability factor
                  <InfoTooltip
                    label="About vulnerability factor"
                    text="Demand multiplier from WorldPop age shares: elderly (+15%) and children (+10%) increase estimated need. Shows 1.0 when census data is not cached for this zone."
                  />
                </dt>
                <dd className="font-medium">
                  {displayedVulnerability?.available
                    ? displayedVulnerability.factor
                    : "1.0 (neutral)"}
                </dd>
                {displayedZone.vulnerability_data_available && (
                  <dd className="mt-1 text-[var(--text-secondary)]">
                    Elderly {((displayedZone.elderly_share ?? 0) * 100).toFixed(1)}% ·
                    Children {((displayedZone.child_share ?? 0) * 100).toFixed(1)}%
                  </dd>
                )}
              </div>
              <div><dt className="text-[var(--text-muted)]">Status</dt><dd>{displayedZone.status}</dd></div>
              <div>
                <dt className="text-[var(--text-muted)]">Coordinates</dt>
                <dd className="text-[var(--text-secondary)]">
                  {displayedZone.latitude?.toFixed(4)}, {displayedZone.longitude?.toFixed(4)}
                </dd>
              </div>
            </dl>
          )}
        </div>
      </div>
    </div>
  )
}
