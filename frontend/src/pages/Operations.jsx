import { useEffect, useMemo, useState } from "react"
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import { getZones, updateZonePriority } from "../api/zones"
import { getReliefCenters } from "../api/inventory"
import { runAllocation, recalculateZoneAllocation, computeRoute } from "../api/allocation"
import { createMission } from "../api/missions"
import { getFieldTeams } from "../api/fieldTeams"
import Select from "../components/ui/Select"
import PageHeader from "../components/ui/PageHeader"
import FitRouteBounds from "../components/Map/FitRouteBounds"
import { buildMissionResourcesPayload } from "../utils/missionPayload"
import {
  getRouteOverlayLabel,
  getRoutePathOptions,
  resolveRouteDepotId,
  routePolylinePositions,
} from "../utils/routeUtils"

const PRIORITIES = ["Critical", "High", "Moderate", "Low"]

export default function Operations() {
  const [zones, setZones] = useState([])
  const [depots, setDepots] = useState([])
  const [teams, setTeams] = useState([])
  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const [priorityDraft, setPriorityDraft] = useState("Moderate")
  const [allocation, setAllocation] = useState(null)
  const [route, setRoute] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [missionNotice, setMissionNotice] = useState("")

  useEffect(() => {
    let cancelled = false
    Promise.all([getZones(), getReliefCenters(), getFieldTeams()])
      .then(([zoneData, depotData, teamData]) => {
        if (cancelled) return
        setZones(zoneData)
        setDepots(depotData)
        setTeams(teamData)
        if (zoneData.length > 0) {
          setSelectedZoneId(zoneData[0].id)
          setPriorityDraft(zoneData[0].operational_priority || zoneData[0].severity)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const selectedZone = useMemo(
    () => zones.find((zone) => zone.id === selectedZoneId),
    [zones, selectedZoneId],
  )

  const routeDepot = useMemo(() => {
    if (!route) {
      return null;
    }
    return depots.find((depot) => depot.id === route.depot_id) ?? null;
  }, [depots, route]);

  const routePositions = useMemo(
    () => routePolylinePositions(route),
    [route],
  );

  async function handleOptimize() {
    setLoading(true)
    setError("")
    setMissionNotice("")
    try {
      const result = await runAllocation(selectedZoneId ? [selectedZoneId] : null)
      if (result.status === "insufficient_inventory") {
        setError(result.message || "Insufficient inventory for allocation.")
      }
      setAllocation(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handlePriorityOverride() {
    if (!selectedZoneId) return
    setLoading(true)
    setError("")
    try {
      await updateZonePriority(selectedZoneId, priorityDraft)
      const result = await recalculateZoneAllocation(selectedZoneId)
      setAllocation(result)
      const refreshed = await getZones()
      setZones(refreshed)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRoute() {
    if (!selectedZoneId || depots.length === 0) return
    setLoading(true)
    setError("")
    try {
      const depotId = resolveRouteDepotId(
        allocation,
        selectedZoneId,
        depots,
        selectedZone,
      )
      const routeData = await computeRoute(depotId, selectedZoneId)
      setRoute(routeData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateMission() {
    if (!selectedZoneId || depots.length === 0) return
    if (!allocation || allocation.status !== "ok") {
      setError("Run optimization successfully before creating a mission.")
      return
    }

      const resourcesPayload = buildMissionResourcesPayload(allocation, selectedZoneId)
      if (!resourcesPayload) {
        setError("Allocation results are missing. Run optimization again.")
        return
      }

      const flowDepotId = resourcesPayload.flows?.[0]?.relief_center_id
      const depotId = flowDepotId ?? depots[0].id

      setLoading(true)
      setError("")
      try {
        const teamId = teams[0]?.id ?? null
        const mission = await createMission({
          zone_id: selectedZoneId,
          field_team_id: teamId,
          relief_center_id: depotId,
          priority: priorityDraft,
          resources_payload: resourcesPayload,
        })
      setMissionNotice(`Mission ${mission.mission_code} created.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <PageHeader
        title="Resource Allocation"
        subtitle="Optimize supply against M2 demand, override priority, route, and create missions"
      />

      {error && (
        <div className="rounded-md border border-[var(--critical)] bg-red-50 px-3 py-2 text-xs text-[var(--critical)] dark:bg-red-950/30">
          {error}
        </div>
      )}
      {missionNotice && (
        <div className="rounded-md border border-[var(--success)] px-3 py-2 text-xs text-[var(--success)]">
          {missionNotice}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        <div className="ops-card space-y-2 p-3">
          <h2 className="text-sm font-semibold">Zone & Priority</h2>
          <ol className="mb-2 list-decimal space-y-0.5 pl-4 text-xs text-[var(--text-muted)]">
            <li>Select zone and priority</li>
            <li>Run optimization</li>
            <li>Override if needed</li>
            <li>Generate route</li>
            <li>Create mission</li>
          </ol>
          <Select
            value={selectedZoneId ?? ""}
            onChange={(e) => {
              const zoneId = Number(e.target.value)
              setSelectedZoneId(zoneId)
              const zone = zones.find((item) => item.id === zoneId)
              setPriorityDraft(zone?.operational_priority || zone?.severity || "Moderate")
            }}
          >
            {zones.map((zone) => (
              <option key={zone.id} value={zone.id}>
                {zone.zone_name} ({zone.operational_priority || zone.severity})
              </option>
            ))}
          </Select>

          <Select value={priorityDraft} onChange={(e) => setPriorityDraft(e.target.value)}>
            {PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>{priority}</option>
            ))}
          </Select>

          <div className="flex flex-wrap gap-2">
            <button className="ops-btn ops-btn-primary" onClick={handleOptimize} disabled={loading}>Run Optimization</button>
            <button className="ops-btn bg-[var(--medium)] text-white" onClick={handlePriorityOverride} disabled={loading}>Override & Recalculate</button>
            <button className="ops-btn bg-[var(--surface-elevated)] text-[var(--text-primary)] border border-[var(--border)]" onClick={handleRoute} disabled={loading}>Generate Route</button>
            <button className="ops-btn bg-[var(--success)] text-white" onClick={handleCreateMission} disabled={loading}>Create Mission</button>
          </div>
        </div>

        <div className="ops-card xl:col-span-2 p-3">
          <h2 className="mb-2 text-sm font-semibold">Allocation Plan</h2>
          {!allocation ? (
            <p className="text-xs text-[var(--text-muted)]">Run optimization to view allocation results.</p>
          ) : (
            <div className="space-y-2">
              <p className="text-xs">
                Status: <strong>{allocation.status}</strong> | Coverage: <strong>{(allocation.coverage_ratio * 100).toFixed(1)}%</strong>
              </p>
              <div className="overflow-x-auto">
                <table className="ops-table min-w-full text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-left">
                      <th className="py-1 pr-2">Zone</th>
                      <th className="py-1 pr-2">Category</th>
                      <th className="py-1 pr-2">Demanded</th>
                      <th className="py-1 pr-2">Allocated</th>
                      <th className="py-1 pr-2">Unmet</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allocation.allocations.map((row, index) => (
                      <tr key={`${row.zone_id}-${row.resource_category}-${index}`} className="border-b border-[var(--border)]">
                        <td className="py-1 pr-2">{row.zone_id}</td>
                        <td className="py-1 pr-2">{row.resource_category}</td>
                        <td className="py-1 pr-2">{row.demanded}</td>
                        <td className="py-1 pr-2">{row.allocated}</td>
                        <td className="py-1 pr-2">{row.unmet}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {route && selectedZone && routeDepot && routePositions.length > 0 && (
        <div className="ops-card p-3">
          <h2 className="mb-1 text-sm font-semibold">Route Overlay</h2>
          <p className="mb-1 text-xs text-[var(--text-muted)]">
            {getRouteOverlayLabel(route)}
            {route.routing_label ? ` — ${route.routing_label}` : ""}
          </p>
          <p className="mb-2 text-xs text-[var(--text-muted)]">
            {route.depot_name} → {route.zone_name}: {route.distance_km} km, ETA {route.estimated_travel_hours} h ({route.route_status})
            {routePositions.length > 2 ? ` · ${routePositions.length} path points` : ""}
          </p>
          <div className="h-64 overflow-hidden rounded-md border border-[var(--border)]">
            <MapContainer
              center={routePositions[0]}
              zoom={10}
              className="h-full w-full"
              scrollWheelZoom
              doubleClickZoom
              dragging
              zoomControl
            >
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <FitRouteBounds positions={routePositions} />
              <Marker position={[routeDepot.latitude, routeDepot.longitude]}>
                <Popup>{routeDepot.name}</Popup>
              </Marker>
              <Marker position={[selectedZone.latitude, selectedZone.longitude]}>
                <Popup>{selectedZone.zone_name}</Popup>
              </Marker>
              <Polyline
                positions={routePositions}
                pathOptions={getRoutePathOptions(route)}
              />
            </MapContainer>
          </div>
        </div>
      )}
    </div>
  )
}
