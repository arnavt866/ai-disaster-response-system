import { useEffect, useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import StatCard from "../Cards/StatCard"
import ResourceChart from "../Charts/ResourceChart"
import DisasterMap from "../Map/DisasterMap"
import PageHeader from "../ui/PageHeader"
import Badge from "../ui/Badge"
import { severityBadge } from "../../utils/badgeUtils"
import { Activity, Users, Package, TriangleAlert } from "lucide-react"
import { getDashboardMetrics } from "../../api/analytics"
import { getDisaster } from "../../api/disasters"
import { getInventory } from "../../api/inventory"
import { getMissions } from "../../api/missions"
import { getZones } from "../../api/zones"
import { formatDisasterType } from "../../utils/disasterHelpers"

function Dashboard() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedDisasterId = searchParams.get("disasterId")
  const focusLat = searchParams.get("lat") ? Number(searchParams.get("lat")) : null
  const focusLon = searchParams.get("lon") ? Number(searchParams.get("lon")) : null
  const focusZoom = searchParams.get("zoom") ? Number(searchParams.get("zoom")) : 10
  const [metrics, setMetrics] = useState(null)
  const [inventory, setInventory] = useState([])
  const [missions, setMissions] = useState([])
  const [zones, setZones] = useState([])
  const [disasterCache, setDisasterCache] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getDashboardMetrics(), getInventory(), getMissions(), getZones()])
      .then(([dashboard, stock, missionRows, zoneRows]) => {
        setMetrics(dashboard)
        setInventory(stock)
        setMissions(missionRows)
        setZones(zoneRows)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedDisasterId) return undefined
    let cancelled = false
    getDisaster(Number(selectedDisasterId))
      .then((data) => {
        if (!cancelled) {
          setDisasterCache((prev) => ({ ...prev, [selectedDisasterId]: data }))
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [selectedDisasterId])

  const fetchedDisaster = selectedDisasterId ? disasterCache[selectedDisasterId] : null

  const zoneMap = useMemo(() => Object.fromEntries(zones.map((z) => [z.id, z.zone_name])), [zones])

  const chartData = useMemo(() => {
    const grouped = {}
    inventory.forEach((item) => {
      const key = String(item.category || "other").toLowerCase()
      grouped[key] = (grouped[key] || 0) + item.quantity
    })
    return Object.entries(grouped).map(([name, units]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      units,
    }))
  }, [inventory])

  function handleDisasterSelect(disasterId) {
    setSearchParams({ disasterId: String(disasterId) })
  }

  return (
    <div className="space-y-2">
      <PageHeader
        title="Disaster Response Command Center"
        subtitle="Operational overview from live backend data"
      />

      <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
        <StatCard
          title="Active Zones"
          value={loading ? "—" : String(metrics?.active_zones ?? 0)}
          icon={Activity}
          description="Active disaster zones"
          onClick={() => navigate("/zones")}
        />
        <StatCard
          title="Affected Population"
          value={loading ? "—" : (metrics?.affected_population ?? 0).toLocaleString()}
          icon={Users}
          description="Across active zones"
        />
        <StatCard
          title="Available Stock"
          value={loading ? "—" : String(metrics?.available_resources ?? 0)}
          icon={Package}
          description="Units ready to allocate"
          onClick={() => navigate("/resources")}
        />
        <StatCard
          title="Critical Zones"
          value={loading ? "—" : String(metrics?.critical_zones ?? 0)}
          icon={TriangleAlert}
          description="Commander priority critical"
          onClick={() => navigate("/zones?priority=Critical")}
        />
      </div>

      <div className="grid grid-cols-1 gap-2 xl:grid-cols-3">
        <div className="ops-card p-2 xl:col-span-2">
          <h2 className="mb-1 px-1 text-sm font-semibold">Global Disaster Map</h2>
          <p className="mb-1.5 px-1 text-sm text-[var(--text-muted)]">Click a marker to inspect an incident.</p>
          <div className="h-[300px] overflow-hidden rounded-md">
            <DisasterMap
              selectedDisasterId={selectedDisasterId ? Number(selectedDisasterId) : null}
              onDisasterSelect={handleDisasterSelect}
              focusLat={focusLat}
              focusLon={focusLon}
              focusZoom={focusZoom}
            />
          </div>
        </div>

        <div className="ops-card p-2">
          <h2 className="mb-1.5 text-sm font-semibold">Operational Summary</h2>
          {fetchedDisaster ? (
            <div className="space-y-1.5 text-sm">
              <p className="font-semibold">{fetchedDisaster.title || formatDisasterType(fetchedDisaster.disaster_type)}</p>
              <p>Type: {formatDisasterType(fetchedDisaster.disaster_type)}</p>
              <p>Location: {fetchedDisaster.location || "—"}</p>
              <p>
                Severity:{" "}
                <Badge variant={severityBadge(fetchedDisaster.severity)}>
                  {fetchedDisaster.severity || "Not rated"}
                </Badge>
              </p>
              <p>Status: {fetchedDisaster.status}</p>
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">
              Select a disaster from the map or Disasters page to inspect incident details.
            </p>
          )}
          {metrics && (
            <div className="mt-2 space-y-1 border-t border-[var(--border)] pt-2 text-sm">
              <p>Allocated: {metrics.allocated_resources}</p>
              <p>Reserved: {metrics.reserved_resources ?? 0}</p>
              <p>In transit: {metrics.in_transit_resources ?? 0}</p>
              <p>Unmet demand: {metrics.unmet_demand}</p>
              <button
                type="button"
                className="text-left text-[var(--primary)] hover:underline"
                onClick={() => navigate("/missions")}
              >
                Active missions: {metrics.active_missions}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
        <div className="ops-card p-2">
          <h2 className="mb-1.5 text-sm font-semibold">Inventory by Category</h2>
          <ResourceChart data={chartData} />
        </div>
        <div className="ops-card p-2">
          <h2 className="mb-1.5 text-sm font-semibold">Recent Missions</h2>
          {missions.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">No missions yet.</p>
          ) : (
            <table className="ops-table w-full">
              <thead>
                <tr className="border-b border-[var(--border)] text-left">
                  <th className="py-1.5">Code</th>
                  <th className="py-1.5">Zone</th>
                  <th className="py-1.5">Priority</th>
                  <th className="py-1.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {missions.slice(0, 6).map((mission) => (
                  <tr key={mission.id} className="border-b border-[var(--border)]">
                    <td className="py-1.5 font-mono text-sm">{mission.mission_code}</td>
                    <td className="py-1.5">{zoneMap[mission.zone_id] || mission.zone_id}</td>
                    <td className="py-1.5">
                      <Badge variant={severityBadge(mission.priority)}>{mission.priority}</Badge>
                    </td>
                    <td className="py-1.5">{mission.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
