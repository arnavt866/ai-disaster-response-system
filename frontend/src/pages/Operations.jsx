import { useEffect, useMemo, useState } from "react"
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker } from "react-leaflet"
import { Maximize2, Minimize2 } from "lucide-react"
import "leaflet/dist/leaflet.css"
import { getZones, updateZonePriority } from "../api/zones"
import { getReliefCenters } from "../api/inventory"
import { runAllocation, recalculateZoneAllocation, computeRoute, blockRoadSegment, unblockRoadSegment, clearRoadBlocks, getRoadBlocks } from "../api/allocation"
import { createMission } from "../api/missions"
import { getFieldTeams } from "../api/fieldTeams"
import { getSystemMetadata } from "../api/system"
import Select from "../components/ui/Select"
import PageHeader from "../components/ui/PageHeader"
import FitRouteBounds from "../components/Map/FitRouteBounds"
import { buildMissionResourcesPayload } from "../utils/missionPayload"
import {
  getRouteOverlayLabel,
  getRoutePathOptions,
  resolveRouteDepotId,
  routePolylinePositions,
  sampleRouteBlockPoints,
} from "../utils/routeUtils"
import InfoTooltip from "../components/ui/InfoTooltip"
import AiEngineLabel from "../components/ui/AiEngineLabel"

export default function Operations() {
  const [zones, setZones] = useState([])
  const [depots, setDepots] = useState([])
  const [teams, setTeams] = useState([])
  const [priorities, setPriorities] = useState([])
  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const [priorityDraft, setPriorityDraft] = useState("Moderate")
  const [allocation, setAllocation] = useState(null)
  const [route, setRoute] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [missionNotice, setMissionNotice] = useState("")
  const [roadBlocks, setRoadBlocks] = useState([])
  const [routeRefreshing, setRouteRefreshing] = useState(false)
  const [routeMapFullscreen, setRouteMapFullscreen] = useState(false)

  useEffect(() => {
    let cancelled = false
    Promise.all([getZones(), getReliefCenters(), getFieldTeams(), getSystemMetadata()])
      .then(([zoneData, depotData, teamData, metadata]) => {
        if (cancelled) return
        setZones(zoneData)
        setDepots(depotData)
        setTeams(teamData)
        setPriorities(metadata.operational_priorities || [])
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

  useEffect(() => {
    getRoadBlocks()
      .then((data) => setRoadBlocks(data.blocks || []))
      .catch(() => {})
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

  const routeBlockPoints = useMemo(
    () => sampleRouteBlockPoints(route),
    [route],
  );

  async function handleOptimize() {
    if (!selectedZoneId) {
      setError("Select a disaster zone before running optimization. Full-system runs are not started from this page.")
      return
    }

    setLoading(true)
    setError("")
    setMissionNotice("")
    try {
      const result = await runAllocation([selectedZoneId], true, false)

      if (result.status === "insufficient_inventory") {
        setError(result.message || "Insufficient inventory for allocation.")
      }
      if (result.warning) {
        setMissionNotice(result.warning)
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

  async function refreshRoute() {
    if (!selectedZoneId || depots.length === 0) return null
    setRouteRefreshing(true)
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
      const blocks = await getRoadBlocks(routeData.region_id || undefined)
      setRoadBlocks(blocks.blocks || [])
      return routeData
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setRouteRefreshing(false)
    }
  }

  async function handleRoute() {
    if (!selectedZoneId || depots.length === 0) return
    setLoading(true)
    await refreshRoute()
    setLoading(false)
  }

  async function handleToggleRoadBlock(edge) {
    const key = `${edge.region_id}:${edge.u}:${edge.v}`
    const isBlocked = roadBlocks.some(
      (block) => `${block.region_id}:${block.u}:${block.v}` === key,
    )
    setRouteRefreshing(true)
    setError("")
    try {
      if (isBlocked) {
        await unblockRoadSegment(edge.region_id, edge.u, edge.v)
      } else {
        await blockRoadSegment(edge.region_id, edge.u, edge.v)
      }
      await refreshRoute()
    } catch (err) {
      setError(err.message)
    } finally {
      setRouteRefreshing(false)
    }
  }

  async function handleClearRoadBlocks() {
    if (!route?.region_id) return
    setRouteRefreshing(true)
    setError("")
    try {
      await clearRoadBlocks(route.region_id)
      await refreshRoute()
    } catch (err) {
      setError(err.message)
    } finally {
      setRouteRefreshing(false)
    }
  }

  function isEdgeBlocked(edge) {
    return roadBlocks.some(
      (block) =>
        block.region_id === edge.region_id &&
        String(block.u) === String(edge.u) &&
        String(block.v) === String(edge.v),
    )
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
        subtitle="LP optimization against ML-predicted zone demand — override priority, route, and create missions"
      />

      {error && (
        <div className="rounded-md border border-[var(--critical)] bg-red-50 px-3 py-2 text-[var(--critical)] dark:bg-red-950/30">
          {error}
        </div>
      )}
      {missionNotice && (
        <div className="rounded-md border border-[var(--success)] px-3 py-2 text-[var(--success)]">
          {missionNotice}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        <div className="ops-card space-y-2 p-3">
          <h2 className="ops-section-title">Zone & Priority</h2>
          <ol className="mb-2 list-decimal space-y-0.5 pl-4 ops-muted">
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
            {priorities.map((priority) => (
              <option key={priority} value={priority}>{priority}</option>
            ))}
          </Select>

          <div className="flex flex-wrap items-center gap-2">
            <button className="ops-btn ops-btn-primary" onClick={handleOptimize} disabled={loading || !selectedZoneId}>
              Run Optimization
            </button>
            <AiEngineLabel
              title="Demand inputs come from the zone ML predictor; allocation uses linear programming over depot supply and transport capacity."
            >
              AI-recommended allocation
            </AiEngineLabel>
            <button className="ops-btn bg-[var(--medium)] text-white" onClick={handlePriorityOverride} disabled={loading}>Override & Recalculate</button>
            <button className="ops-btn bg-[var(--surface-elevated)] text-[var(--text-primary)] border border-[var(--border)]" onClick={handleRoute} disabled={loading}>Generate Route</button>
            <button className="ops-btn bg-[var(--success)] text-white" onClick={handleCreateMission} disabled={loading}>Create Mission</button>
          </div>
        </div>

        <div className="ops-card xl:col-span-2 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h2 className="ops-section-title">Allocation Plan</h2>
            {allocation && (
              <AiEngineLabel title="Demanded units are ML predictions; allocated units are LP optimizer output.">
                ML demand · LP optimized
              </AiEngineLabel>
            )}
          </div>
          {!allocation ? (
            <p className="ops-muted">Run optimization to view allocation results.</p>
          ) : (
            <div className="space-y-2">
              <p>
                Status: <strong>{allocation.status}</strong>
                {" | "}
                <span className="inline-flex items-center">
                  Coverage: <strong>{(allocation.coverage_ratio * 100).toFixed(1)}%</strong>
                  <InfoTooltip
                    label="About coverage ratio"
                    text="Fraction of total zone demand fulfilled by this allocation plan (allocated ÷ demanded across all categories)."
                  />
                </span>
              </p>
              <div className="overflow-x-auto">
                <table className="ops-table min-w-full">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-left">
                      <th className="py-1 pr-2">Zone</th>
                      <th className="py-1 pr-2">Category</th>
                      <th className="py-1 pr-2">Demanded</th>
                      <th className="py-1 pr-2">Allocated</th>
                      <th className="py-1 pr-2">
                        <span className="inline-flex items-center">
                          Unmet
                          <InfoTooltip
                            label="About unmet demand"
                            text="Units still needed for this zone and resource category after optimization."
                          />
                        </span>
                      </th>
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
        <div
          className={
            routeMapFullscreen
              ? "fixed inset-0 z-50 flex flex-col bg-[var(--bg)] p-3"
              : "ops-card p-3"
          }
        >
          <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h2 className="ops-section-title">Route Overlay</h2>
              <p className="ops-muted">
                {getRouteOverlayLabel(route)}
                {route.routing_label ? ` — ${route.routing_label}` : ""}
              </p>
              <p className="ops-muted">
                {route.depot_name} → {route.zone_name}: {route.distance_km} km, ETA {route.estimated_travel_hours} h ({route.route_status})
                {routePositions.length > 2 ? ` · ${routePositions.length} path points` : ""}
                {route.routing_method ? ` · ${route.routing_method}` : ""}
              </p>
            </div>
            <button
              type="button"
              className="ops-btn shrink-0 border border-[var(--border)] bg-[var(--surface-elevated)]"
              onClick={() => setRouteMapFullscreen((prev) => !prev)}
              title={routeMapFullscreen ? "Exit fullscreen map" : "Fullscreen map"}
            >
              {routeMapFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </button>
          </div>
          {routeBlockPoints.length > 0 && (
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="ops-muted">
                Click a point on the route to block that segment
                {route.path_edges?.length > routeBlockPoints.length
                  ? ` (${routeBlockPoints.length} of ${route.path_edges.length} shown)`
                  : ""}
                . Blocked edges are avoided on re-route.
              </p>
              <button
                type="button"
                className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)]"
                disabled={routeRefreshing || roadBlocks.length === 0}
                onClick={handleClearRoadBlocks}
              >
                Clear region blocks
              </button>
            </div>
          )}
          {routeBlockPoints.some((point) => isEdgeBlocked(point.edge)) && (
            <ul className="mb-2 flex flex-wrap gap-1">
              {routeBlockPoints.filter((point) => isEdgeBlocked(point.edge)).map((point) => (
                <li key={`${point.edge.region_id}-${point.edge.u}-${point.edge.v}`}>
                  <button
                    type="button"
                    className="ops-btn bg-[var(--critical)] px-2 py-1 text-white"
                    disabled={routeRefreshing}
                    onClick={() => handleToggleRoadBlock(point.edge)}
                  >
                    Unblock seg {point.index + 1}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div
            className={
              routeMapFullscreen
                ? "min-h-0 flex-1 overflow-hidden rounded-md border border-[var(--border)]"
                : "h-[min(58vh,680px)] min-h-[24rem] overflow-hidden rounded-md border border-[var(--border)]"
            }
          >
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
              {routeBlockPoints.map((point) => {
                const blocked = isEdgeBlocked(point.edge)
                return (
                  <CircleMarker
                    key={`${point.edge.region_id}-${point.edge.u}-${point.edge.v}`}
                    center={[point.lat, point.lon]}
                    radius={blocked ? 9 : 7}
                    pathOptions={{
                      color: blocked ? "var(--severity-critical)" : "var(--accent)",
                      fillColor: blocked ? "var(--severity-critical)" : "var(--accent)",
                      fillOpacity: 0.9,
                      weight: 2,
                    }}
                    eventHandlers={{
                      click: () => {
                        if (!routeRefreshing) handleToggleRoadBlock(point.edge)
                      },
                    }}
                  >
                    <Popup>
                      Segment {point.index + 1}
                      {point.edge.length_m != null ? ` · ${point.edge.length_m} m` : ""}
                      <br />
                      Click the marker to {blocked ? "unblock" : "block"} this segment.
                    </Popup>
                  </CircleMarker>
                )
              })}
            </MapContainer>
          </div>
        </div>
      )}
    </div>
  )
}
