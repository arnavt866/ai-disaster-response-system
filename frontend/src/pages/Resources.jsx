import { useEffect, useMemo, useState } from "react"
import { getInventory, getReliefCenters } from "../api/inventory"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import SearchInput from "../components/ui/SearchInput"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { ErrorState } from "../components/ui/StateMessage"
import usePagination from "../hooks/usePagination"
import useResponsivePageSize from "../hooks/useResponsivePageSize"

function normalizeDepotName(name) {
  return (name || "").trim().toLowerCase()
}

function aggregateByDepotCategory(items) {
  const grouped = new Map()
  items.forEach((item) => {
    if ((item.status || "").toLowerCase() !== "available") return
    const key = `${item.warehouse}::${String(item.category || "").toLowerCase()}`
    const existing = grouped.get(key)
    if (existing) {
      existing.quantity += item.quantity || 0
      existing.reserved_quantity += item.reserved_quantity || 0
      existing.in_transit_quantity += item.in_transit_quantity || 0
      existing.record_count += 1
    } else {
      grouped.set(key, {
        id: key,
        resource_name: `${String(item.category || "resource").toUpperCase()} stock`,
        category: item.category,
        quantity: item.quantity || 0,
        reserved_quantity: item.reserved_quantity || 0,
        in_transit_quantity: item.in_transit_quantity || 0,
        warehouse: item.warehouse,
        record_count: 1,
      })
    }
  })
  return [...grouped.values()]
}

function ResourceTableCard({ title, subtitle, children, pagination }) {
  return (
    <div className="ops-card overflow-hidden">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="ops-section-title">{title}</h2>
        {subtitle && <p className="ops-muted">{subtitle}</p>}
      </div>
      <div className="overflow-x-auto">{children}</div>
      {pagination}
    </div>
  )
}

export default function Resources() {
  const [inventory, setInventory] = useState([])
  const [depots, setDepots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [viewMode, setViewMode] = useState("aggregated")
  const [searchTerm, setSearchTerm] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("All")
  const [statusFilter, setStatusFilter] = useState("All")
  const [depotFilter, setDepotFilter] = useState("All")
  const [depotStatusFilter, setDepotStatusFilter] = useState("All")

  useEffect(() => {
    let cancelled = false
    Promise.all([getInventory(), getReliefCenters()])
      .then(([stock, centers]) => {
        if (!cancelled) {
          setInventory(stock)
          setDepots(centers)
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

  const inventoryRows = useMemo(() => {
    if (viewMode === "aggregated") {
      return aggregateByDepotCategory(inventory)
    }
    return inventory
  }, [inventory, viewMode])

  const inventoryByDepot = useMemo(() => {
    const totals = {}
    inventory.forEach((item) => {
      if ((item.status || "").toLowerCase() !== "available") return
      const key = normalizeDepotName(item.warehouse)
      totals[key] = (totals[key] || 0) + (item.quantity || 0)
    })
    return totals
  }, [inventory])

  const groupedDepots = useMemo(() => {
    const groups = new Map()
    depots.forEach((depot) => {
      const depotStatus = (depot.status || "").toLowerCase()
      if (depotStatus === "quarantined") return

      const key = normalizeDepotName(depot.name)
      const existing = groups.get(key)
      const isActive = depotStatus === "active"
      if (existing) {
        existing.entries.push(depot)
        existing.rawNames.add(depot.name)
        if (isActive) {
          existing.totalCapacity += depot.capacity || 0
          existing.totalAvailable += depot.available_capacity || 0
          existing.status = depot.status
          existing.latitude = depot.latitude
          existing.longitude = depot.longitude
          existing.displayName = depot.name
        } else {
          existing.inactiveVariants += 1
        }
      } else {
        groups.set(key, {
          id: key,
          displayName: depot.name,
          entries: [depot],
          rawNames: new Set([depot.name]),
          totalCapacity: isActive ? depot.capacity || 0 : 0,
          totalAvailable: isActive ? depot.available_capacity || 0 : 0,
          inactiveVariants: isActive ? 0 : 1,
          status: depot.status,
          latitude: depot.latitude,
          longitude: depot.longitude,
        })
      }
    })
    return [...groups.values()]
  }, [depots])

  const categoryOptions = useMemo(
    () => ["All", ...new Set(inventory.map((item) => item.category).filter(Boolean))],
    [inventory],
  )

  const statusOptions = useMemo(
    () => ["All", ...new Set(inventory.map((item) => item.status).filter(Boolean))],
    [inventory],
  )

  const depotOptions = useMemo(
    () => ["All", ...new Set(inventory.map((item) => item.warehouse).filter(Boolean))],
    [inventory],
  )

  const depotStatusOptions = useMemo(
    () => ["All", ...new Set(depots.map((depot) => depot.status).filter(Boolean))],
    [depots],
  )

  const filteredInventoryRows = useMemo(() => {
    const search = searchTerm.trim().toLowerCase()
    return inventoryRows.filter((item) => {
      const matchesSearch =
        !search ||
        item.resource_name?.toLowerCase().includes(search) ||
        item.category?.toLowerCase().includes(search) ||
        item.warehouse?.toLowerCase().includes(search)
      const matchesCategory = categoryFilter === "All" || item.category === categoryFilter
      const matchesStatus = statusFilter === "All" || item.status === statusFilter
      const matchesDepot = depotFilter === "All" || item.warehouse === depotFilter
      return matchesSearch && matchesCategory && matchesStatus && matchesDepot
    })
  }, [inventoryRows, searchTerm, categoryFilter, statusFilter, depotFilter])

  const filteredDepots = useMemo(() => {
    const search = searchTerm.trim().toLowerCase()
    return groupedDepots.filter((group) => {
      const displayName = group.displayName?.toLowerCase() || ""
      const variantNames = [...group.rawNames].some((name) =>
        name.toLowerCase().includes(search),
      )
      const matchesSearch = !search || displayName.includes(search) || variantNames
      const matchesStatus =
        depotStatusFilter === "All" || group.status === depotStatusFilter
      return matchesSearch && matchesStatus
    })
  }, [groupedDepots, searchTerm, depotStatusFilter])

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
  } = usePagination(filteredInventoryRows, pageSize)

  const {
    page: depotPage,
    pageItems: depotPageItems,
    totalPages: depotTotalPages,
    totalItems: depotTotalItems,
    rangeStart: depotRangeStart,
    rangeEnd: depotRangeEnd,
    goToPage: goToDepotPage,
    resetPage: resetDepotPage,
    hasPrevious: depotHasPrevious,
    hasNext: depotHasNext,
  } = usePagination(filteredDepots, pageSize)

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Resources & Depots" subtitle="Inventory quantities and relief center locations" />
        <p className="text-[var(--text-secondary)]">Loading resources...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <PageHeader
        title="Resources & Depots"
        subtitle={`${inventory.length} inventory records across ${depots.length} depots`}
      />
      {error && <ErrorState title="Unable to load resources" message={error} />}

      <div className="ops-card p-3">
        <h2 className="mb-2 ops-section-label">Search & Filters</h2>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
          <SearchInput
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              resetPage()
              resetDepotPage()
            }}
            placeholder="Search resource, category, or depot..."
          />
          <Select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value)
              resetPage()
            }}
          >
            <option value="All">All Categories</option>
            {categoryOptions.filter((value) => value !== "All").map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </Select>
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              resetPage()
            }}
          >
            <option value="All">All Inventory Statuses</option>
            {statusOptions.filter((value) => value !== "All").map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
          <Select
            value={depotFilter}
            onChange={(e) => {
              setDepotFilter(e.target.value)
              resetPage()
            }}
          >
            <option value="All">All Depots</option>
            {depotOptions.filter((value) => value !== "All").map((depot) => (
              <option key={depot} value={depot}>
                {depot}
              </option>
            ))}
          </Select>
        </div>
        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
          <div className="flex items-center gap-2">
            <label className="shrink-0 ops-muted">Inventory view</label>
            <Select className="max-w-xs" value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
              <option value="aggregated">By Depot + Category (summed)</option>
              <option value="records">Individual Records</option>
            </Select>
          </div>
          <Select
            value={depotStatusFilter}
            onChange={(e) => {
              setDepotStatusFilter(e.target.value)
              resetDepotPage()
            }}
          >
            <option value="All">All Depot Statuses</option>
            {depotStatusOptions.filter((value) => value !== "All").map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <ResourceTableCard
          title="Inventory"
          subtitle={
            viewMode === "aggregated"
              ? "Quantities summed per depot and category from backend records."
              : undefined
          }
          pagination={
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
          }
        >
          <table className="ops-table min-w-full">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th>Resource</th>
                <th>Category</th>
                <th>Available</th>
                <th>Reserved</th>
                <th>In Transit</th>
                <th>Depot</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-[var(--text-secondary)]">
                    No inventory records yet.
                  </td>
                </tr>
              ) : (
                pageItems.map((item) => (
                  <tr key={item.id} className="border-b border-[var(--border)]">
                    <td>{item.resource_name}</td>
                    <td className="capitalize">{item.category}</td>
                    <td className="font-medium">{item.quantity?.toLocaleString()}</td>
                    <td>{item.reserved_quantity ?? 0}</td>
                    <td>{item.in_transit_quantity ?? 0}</td>
                    <td>{item.warehouse}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </ResourceTableCard>

        <ResourceTableCard
          title="Relief Centers / Depots"
          pagination={
            <Pagination
              page={depotPage}
              totalPages={depotTotalPages}
              totalItems={depotTotalItems}
              rangeStart={depotRangeStart}
              rangeEnd={depotRangeEnd}
              onPageChange={goToDepotPage}
              hasPrevious={depotHasPrevious}
              hasNext={depotHasNext}
            />
          }
        >
          <table className="ops-table min-w-full">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th>Name</th>
                <th>Capacity</th>
                <th>Available</th>
                <th>Status</th>
                <th>Location</th>
              </tr>
            </thead>
            <tbody>
              {depotPageItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-[var(--text-secondary)]">
                    No relief centers configured.
                  </td>
                </tr>
              ) : (
                depotPageItems.map((group) => {
                  const stockTotal = inventoryByDepot[group.id] ?? 0
                  const capacityMismatch =
                    group.totalAvailable > 0 && stockTotal > group.totalAvailable * 1.5
                  return (
                    <tr key={group.id} className="border-b border-[var(--border)]">
                      <td className="font-medium">
                        {group.displayName}
                        {group.inactiveVariants > 0 && (
                          <Badge variant="warning" className="ml-2">
                            {group.inactiveVariants} quarantined
                          </Badge>
                        )}
                        {capacityMismatch && (
                          <Badge
                            variant="medium"
                            className="ml-2"
                            title={`Listed stock (${stockTotal}) exceeds depot available capacity (${group.totalAvailable})`}
                          >
                            Stock mismatch
                          </Badge>
                        )}
                      </td>
                      <td>{group.totalCapacity?.toLocaleString()}</td>
                      <td>{group.totalAvailable?.toLocaleString()}</td>
                      <td>{group.status}</td>
                      <td className="text-[var(--text-secondary)]">
                        {group.latitude?.toFixed(3)}, {group.longitude?.toFixed(3)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </ResourceTableCard>
      </div>
    </div>
  )
}
