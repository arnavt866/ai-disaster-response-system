import { useEffect, useMemo, useState } from "react"
import { Eye } from "lucide-react"
import { Link } from "react-router-dom"
import { getDisasters } from "../api/disasters"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import SearchInput from "../components/ui/SearchInput"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { LoadingState, ErrorState } from "../components/ui/StateMessage"
import usePagination from "../hooks/usePagination"
import {
  formatDisasterType,
  formatEventTime,
  getSeverityLabel,
  getSeverityVariant,
  matchesSeverityFilter,
  uniqueSorted,
  uniqueSeverities,
} from "../utils/disasterHelpers"

const PAGE_SIZE = 10

export default function Disasters() {
  const [disasters, setDisasters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const [typeFilter, setTypeFilter] = useState("All")
  const [severityFilter, setSeverityFilter] = useState("All")

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
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Location</th>
                <th className="px-3 py-2">Severity</th>
                <th className="px-3 py-2">Date/Time</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Action</th>
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
                    <td className="px-3 py-2 font-medium">
                      {formatDisasterType(disaster.disaster_type)}
                    </td>
                    <td className="max-w-xs truncate px-3 py-2 text-[var(--text-secondary)]">
                      {disaster.location || `${disaster.latitude?.toFixed(3)}, ${disaster.longitude?.toFixed(3)}`}
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant={getSeverityVariant(disaster.severity)}>
                        {getSeverityLabel(disaster.severity)}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-[var(--text-secondary)]">
                      {formatEventTime(disaster.event_time)}
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant={disaster.status === "Active" ? "success" : "neutral"}>
                        {disaster.status || "—"}
                      </Badge>
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/?disasterId=${disaster.id}`}
                        className="inline-flex items-center gap-1 text-sm font-medium text-[var(--primary)] hover:underline"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        View
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
    </div>
  )
}
