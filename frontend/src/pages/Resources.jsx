import { useEffect, useMemo, useState } from "react"
import { getInventory, getReliefCenters } from "../api/inventory"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import SearchInput from "../components/ui/SearchInput"
import Pagination from "../components/ui/Pagination"
import Badge from "../components/ui/Badge"
import { ErrorState } from "../components/ui/StateMessage"
import usePagination from "../hooks/usePagination"

const PAGE_SIZE = 10

function normalizeDepotName(name) {
  return (name || "").trim().toLowerCase()
}

function aggregateByDepotCategory(items) {
  const grouped = new Map()
  items.forEach((item) => {
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

export default function Resources() {
  const [inventory, setInventory] = useState([])
  const [depots, setDepots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [viewMode, setViewMode] = useState("aggregated")
  const [searchTerm, setSearchTerm] = useState("")

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
      const key = normalizeDepotName(item.warehouse)
      totals[key] = (totals[key] || 0) + (item.quantity || 0)
    })
    return totals
  }, [inventory])

  const groupedDepots = useMemo(() => {
    const groups = new Map()
    depots.forEach((depot) => {
      const key = normalizeDepotName(depot.name)
      const existing = groups.get(key)
      if (existing) {
        existing.entries.push(depot)
        existing.rawNames.add(depot.name)
        existing.totalCapacity += depot.capacity || 0
        existing.totalAvailable += depot.available_capacity || 0
      } else {
        groups.set(key, {
          id: key,
          displayName: depot.name,
          entries: [depot],
          rawNames: new Set([depot.name]),
          totalCapacity: depot.capacity || 0,
          totalAvailable: depot.available_capacity || 0,
          status: depot.status,
          latitude: depot.latitude,
          longitude: depot.longitude,
        })
      }
    })
    return [...groups.values()]
  }, [depots])

  const filteredInventoryRows = useMemo(() => {
    const search = searchTerm.trim().toLowerCase()
    if (!search) return inventoryRows
    return inventoryRows.filter((item) => {
      const resourceName = item.resource_name?.toLowerCase() || ""
      const category = item.category?.toLowerCase() || ""
      const depot = item.warehouse?.toLowerCase() || ""
      return (
        resourceName.includes(search) ||
        category.includes(search) ||
        depot.includes(search)
      )
    })
  }, [inventoryRows, searchTerm])

  const filteredDepots = useMemo(() => {
    const search = searchTerm.trim().toLowerCase()
    if (!search) return groupedDepots
    return groupedDepots.filter((group) => {
      const displayName = group.displayName?.toLowerCase() || ""
      const variantNames = [...group.rawNames].some((name) =>
        name.toLowerCase().includes(search),
      )
      return displayName.includes(search) || variantNames
    })
  }, [groupedDepots, searchTerm])

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
  } = usePagination(filteredInventoryRows, PAGE_SIZE)

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
  } = usePagination(filteredDepots, PAGE_SIZE)

  if (loading) {
    return (
      <div className="space-y-3">
        <PageHeader title="Resources & Depots" subtitle="Inventory quantities and relief center locations" />
        <p className="text-sm text-[var(--text-muted)]">Loading resources...</p>
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
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <SearchInput
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              resetPage()
              resetDepotPage()
            }}
            placeholder="Search resource, category, or depot..."
          />
          <div className="flex items-center gap-2">
            <label className="shrink-0 text-sm text-[var(--text-muted)]">Inventory view</label>
            <Select className="max-w-xs" value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
              <option value="aggregated">By Depot + Category (summed)</option>
              <option value="records">Individual Records</option>
            </Select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="ops-card overflow-hidden">
          <div className="border-b border-[var(--border)] px-3 py-2">
            <h2 className="text-sm font-semibold">Inventory</h2>
            {viewMode === "aggregated" && (
              <p className="text-sm text-[var(--text-muted)]">
                Quantities summed per depot and category from backend records.
              </p>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="ops-table min-w-full">
              <thead>
                <tr className="border-b border-[var(--border)] text-left">
                  <th className="px-3 py-2">Resource</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Available</th>
                  <th className="px-3 py-2">Reserved</th>
                  <th className="px-3 py-2">In Transit</th>
                  <th className="px-3 py-2">Depot</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-sm text-[var(--text-muted)]">
                      No inventory records yet.
                    </td>
                  </tr>
                ) : (
                  pageItems.map((item) => (
                    <tr key={item.id} className="border-b border-[var(--border)]">
                      <td className="px-3 py-2">{item.resource_name}</td>
                      <td className="px-3 py-2 capitalize">{item.category}</td>
                      <td className="px-3 py-2 font-medium">{item.quantity?.toLocaleString()}</td>
                      <td className="px-3 py-2">{item.reserved_quantity ?? 0}</td>
                      <td className="px-3 py-2">{item.in_transit_quantity ?? 0}</td>
                      <td className="px-3 py-2">{item.warehouse}</td>
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

        <div className="ops-card overflow-hidden">
          <div className="border-b border-[var(--border)] px-3 py-2">
            <h2 className="text-sm font-semibold">Relief Centers / Depots</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="ops-table min-w-full">
              <thead>
                <tr className="border-b border-[var(--border)] text-left">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Capacity</th>
                  <th className="px-3 py-2">Available</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Location</th>
                </tr>
              </thead>
              <tbody>
                {depotPageItems.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-sm text-[var(--text-muted)]">
                      No relief centers configured.
                    </td>
                  </tr>
                ) : (
                  depotPageItems.map((group) => {
                    const stockTotal = inventoryByDepot[group.id] ?? 0
                    const capacityMismatch = group.totalAvailable > 0 && stockTotal > group.totalAvailable * 1.5
                    return (
                      <tr key={group.id} className="border-b border-[var(--border)]">
                        <td className="px-3 py-2 font-medium">
                          {group.displayName}
                          {group.rawNames.size > 1 && (
                            <Badge variant="warning" className="ml-2">
                              {group.rawNames.size} variants
                            </Badge>
                          )}
                          {capacityMismatch && (
                            <Badge variant="medium" className="ml-2" title={`Listed stock (${stockTotal}) exceeds depot available capacity (${group.totalAvailable})`}>
                              Stock mismatch
                            </Badge>
                          )}
                        </td>
                        <td className="px-3 py-2">{group.totalCapacity?.toLocaleString()}</td>
                        <td className="px-3 py-2">{group.totalAvailable?.toLocaleString()}</td>
                        <td className="px-3 py-2">{group.status}</td>
                        <td className="px-3 py-2 text-sm text-[var(--text-secondary)]">
                          {group.latitude?.toFixed(3)}, {group.longitude?.toFixed(3)}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
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
        </div>
      </div>
    </div>
  )
}
