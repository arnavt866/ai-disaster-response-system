import { useEffect, useMemo, useState } from "react"
import { Eye, FileText } from "lucide-react"
import { Link } from "react-router-dom"
import DownloadReportButton, { REPORT_ACTION_CLASS } from "../components/ui/DownloadReportButton"
import { getDisasters, getDisasterZoneAdvisory } from "../api/disasters"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import SearchInput from "../components/ui/SearchInput"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { LoadingState, ErrorState } from "../components/ui/StateMessage"
import usePagination from "../hooks/usePagination"
import useResponsivePageSize from "../hooks/useResponsivePageSize"
import {
  formatDisasterType,
  formatEventTime,
  getSeverityLabel,
  getSeverityVariant,
  matchesSeverityFilter,
  uniqueSorted,
  uniqueSeverities,
} from "../utils/disasterHelpers"

// Row actions share one treatment so Download Report no longer sits at a
// different visual weight from Advisory / View / Report.
const ROW_ACTION_CLASS = REPORT_ACTION_CLASS

export default function Disasters() {
  const [disasters, setDisasters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const [typeFilter, setTypeFilter] = useState("All")
  const [severityFilter, setSeverityFilter] = useState("All")
  const [advisoryDisasterId, setAdvisoryDisasterId] = useState(null)
  const [advisory, setAdvisory] = useState(null)
  const [advisoryLoading, setAdvisoryLoading] = useState(false)
  const [advisoryError, setAdvisoryError] = useState("")

  useEffect(() => {
    let cancelled = false
    getDisasters()
      .then((data) => {
        if (!cancelled) setDisasters(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Unable to load disaster data.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const disasterTypes = useMemo(
    () => ["All", ...uniqueSorted(disasters.map((d) => d.disaster_type))],
    [disasters],
  )

  const severityOptions = useMemo(
    () => ["All", ...uniqueSeverities(disasters)],
    [disasters],
  )

  const filtered = useMemo(() => {
    const search = searchTerm.trim().toLowerCase()
    return disasters.filter((disaster) => {
      const typeLabel = formatDisasterType(disaster.disaster_type)
      const matchesSearch =
        !search ||
        typeLabel.toLowerCase().includes(search) ||
        disaster.location?.toLowerCase().includes(search) ||
        disaster.title?.toLowerCase().includes(search) ||
        disaster.status?.toLowerCase().includes(search)

      const matchesType =
        typeFilter === "All" || disaster.disaster_type === typeFilter

      const matchesSeverity =
        severityFilter === "All" ||
        matchesSeverityFilter(disaster.severity, severityFilter)

      return matchesSearch && matchesType && matchesSeverity
    })
  }, [disasters, searchTerm, typeFilter, severityFilter])

  useEffect(() => {
    if (!advisoryDisasterId) {
      setAdvisory(null)
      return undefined
    }
    let cancelled = false
    setAdvisoryLoading(true)
    setAdvisoryError("")
    getDisasterZoneAdvisory(advisoryDisasterId)
      .then((data) => {
        if (!cancelled) setAdvisory(data)
      })
      .catch((err) => {
        if (!cancelled) setAdvisoryError(err.message)
      })
      .finally(() => {
        if (!cancelled) setAdvisoryLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [advisoryDisasterId])

  function advisoryVariant(level) {
    const value = String(level || "").toLowerCase()
    if (value === "critical") return "critical"
    if (value === "elevated") return "high"
    if (value === "advisory") return "warning"
    return "neutral"
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
    resetPage,
    hasPrevious,
    hasNext,
  } = usePagination(filtered, pageSize)

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Disaster Events" subtitle="Live incident feed from backend disaster service" />
        <LoadingState message="Loading disasters..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-3">
        <PageHeader title="Disaster Events" subtitle="Live incident feed from backend disaster service" />
        <ErrorState title="Unable to load disaster data." message={error} />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <PageHeader
        title="Disaster Events"
        subtitle={`${disasters.length} incidents tracked — country field not provided by backend API`}
      />

      <div className="ops-card p-3">
        <h2 className="mb-2 text-sm font-semibold text-[var(--text-secondary)]">Search & Filters</h2>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
          <SearchInput
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              resetPage()
            }}
            placeholder="Search type, location, or title..."
          />
          <Select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); resetPage() }}>
            {disasterTypes.map((type) => (
              <option key={type} value={type}>
                {type === "All" ? "All Types" : formatDisasterType(type)}
              </option>
            ))}
          </Select>
          <Select value={severityFilter} onChange={(e) => { setSeverityFilter(e.target.value); resetPage() }}>
            {severityOptions.map((severity) => (
              <option key={severity} value={severity}>
                {severity === "All" ? "All Severities" : severity}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="ops-card p-3">
        <h2 className="mb-2 text-sm font-semibold">GDACS Zone Advisory (read-only)</h2>
        <p className="mb-2 text-xs text-[var(--text-muted)]">
          Rule-based proximity + hazard-type scoring for nearby active zones. Does not create or modify zones.
        </p>
        <Select
          className="max-w-md"
          value={advisoryDisasterId ?? ""}
          onChange={(e) => setAdvisoryDisasterId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Select an incident for advisory scoring…</option>
          {disasters.map((disaster) => (
            <option key={disaster.id} value={disaster.id}>
              {formatDisasterType(disaster.disaster_type)} — {disaster.location || disaster.title}
            </option>
          ))}
        </Select>
        {advisoryLoading && (
          <p className="mt-2 text-sm text-[var(--text-muted)]">Scoring nearby zones…</p>
        )}
        {advisoryError && (
          <ErrorState title="Advisory lookup failed" message={advisoryError} />
        )}
        {advisory && !advisoryLoading && (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-[var(--text-muted)]">
              {advisory.title} · {advisory.zones_scored} zones within {advisory.radius_km} km
              {advisory.source ? ` · source: ${advisory.source}` : ""}
            </p>
            {advisory.advisories.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">No active zones within search radius.</p>
            ) : (
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
                {advisory.advisories.map((row) => (
                  <div key={row.zone_id} className="rounded-md border border-[var(--border)] p-2">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">{row.zone_name}</p>
                      <Badge variant={advisoryVariant(row.advisory_level)}>{row.advisory_level}</Badge>
                    </div>
                    <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
                      <dt className="text-[var(--text-muted)]">Distance</dt>
                      <dd>{row.distance_km} km</dd>
                      <dt className="text-[var(--text-muted)]">Type match</dt>
                      <dd>{row.type_match}</dd>
                      <dt className="text-[var(--text-muted)]">Score</dt>
                      <dd>{row.advisory_score}</dd>
                      <dt className="text-[var(--text-muted)]">Zone type</dt>
                      <dd>{formatDisasterType(row.zone_type)}</dd>
                    </dl>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="ops-card overflow-hidden">
        <div className="border-b border-[var(--border)] px-3 py-2">
          <h2 className="text-sm font-semibold">Incident Registry</h2>
          <p className="text-xs text-[var(--text-muted)]">
            {filtered.length === disasters.length
              ? `Showing ${disasters.length} disasters`
              : `${filtered.length} of ${disasters.length} disasters match filters`}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="ops-table min-w-full">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th >Type</th>
                <th >Location</th>
                <th >Severity</th>
                <th >Date/Time</th>
                <th >Status</th>
                <th >Action</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-sm text-[var(--text-muted)]">
                    No disasters found.
                  </td>
                </tr>
              ) : (
                pageItems.map((disaster) => (
                  <tr key={disaster.id} className="border-b border-[var(--border)]">
                    <td className="font-medium">
                      {formatDisasterType(disaster.disaster_type)}
                    </td>
                    <td className="max-w-xs truncatetext-[var(--text-secondary)]">
                      {disaster.location || `${disaster.latitude?.toFixed(3)}, ${disaster.longitude?.toFixed(3)}`}
                    </td>
                    <td >
                      <Badge variant={getSeverityVariant(disaster.severity)}>
                        {getSeverityLabel(disaster.severity)}
                      </Badge>
                    </td>
                    <td className="text-[var(--text-secondary)]">
                      {formatEventTime(disaster.event_time)}
                    </td>
                    <td >
                      <Badge variant={disaster.status === "Active" ? "success" : "neutral"}>
                        {disaster.status || "—"}
                      </Badge>
                    </td>
                    <td>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <button
                          type="button"
                          className={ROW_ACTION_CLASS}
                          onClick={() => setAdvisoryDisasterId(disaster.id)}
                        >
                          Advisory
                        </button>
                        <Link
                          to={`/dashboard?disasterId=${disaster.id}&lat=${disaster.latitude}&lon=${disaster.longitude}&zoom=10`}
                          className={ROW_ACTION_CLASS}
                        >
                          <Eye className="h-4 w-4 shrink-0" aria-hidden />
                          View
                        </Link>
                        <Link to={`/reports/disaster/${disaster.id}`} className={ROW_ACTION_CLASS}>
                          <FileText className="h-4 w-4 shrink-0" aria-hidden />
                          Report
                        </Link>
                        <DownloadReportButton disasterId={disaster.id} />
                      </div>
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
    </div>
  )
}
