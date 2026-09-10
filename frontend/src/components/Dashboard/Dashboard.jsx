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
import { getDisaster, getDisasters, getDisasterZoneAdvisory } from "../../api/disasters"
import { getInventory } from "../../api/inventory"
import { getMissions } from "../../api/missions"
import { getZones } from "../../api/zones"
import { formatDisasterType } from "../../utils/disasterHelpers"
import { pickFallbackInsightZone, resolveZoneForDisaster } from "../../utils/insightZone"
import { pickMapDisasters } from "../../utils/mapDisasters"
import { predictZoneDemand } from "../../api/predictions"
import { getSystemMetadata, demandTargetMaps } from "../../api/system"
import AiEngineLabel from "../ui/AiEngineLabel"
import InfoTooltip from "../ui/InfoTooltip"
import Select from "../ui/Select"
import DownloadReportButton from "../ui/DownloadReportButton"

// Relative stock level -> severity, so the chart encodes scarcity rather than
// rendering every category in one flat colour.
function stockSeverity(share) {
  if (share < 0.25) return "critical"
  if (share < 0.5) return "high"
  if (share < 0.75) return "moderate"
  return "ok"
}

function SummaryRow({ label, value, tooltip, tone }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b border-[var(--border)] py-1 last:border-0">
      <span className="inline-flex items-center ops-section-label">
        {label}
        {tooltip && <InfoTooltip label={`About ${label}`} text={tooltip} />}
      </span>
      <span className={`font-semibold tabular-nums ${tone || "text-[var(--text-primary)]"}`}>
        {value}
      </span>
    </div>
  )
}

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
  const [disasters, setDisasters] = useState([])
  const [disasterCache, setDisasterCache] = useState({})
  const [loading, setLoading] = useState(true)
  const [aiInsight, setAiInsight] = useState({ loading: false, error: "", data: null, zoneName: "" })
  const [targetLabels, setTargetLabels] = useState({})

  useEffect(() => {
    Promise.all([
      getDashboardMetrics(),
      getInventory(),
      getMissions(),
      getZones(),
      getDisasters(),
      getSystemMetadata(),
    ])
      .then(([dashboard, stock, missionRows, zoneRows, disasterRows, metadata]) => {
        setMetrics(dashboard)
        setInventory(stock)
        setMissions(missionRows)
        setZones(zoneRows)
        setDisasters(disasterRows)
        setTargetLabels(demandTargetMaps(metadata).labels)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const effectiveDisasterId =
    selectedDisasterId ?? (disasters[0]?.id != null ? String(disasters[0].id) : null)

  const selectedDisaster = useMemo(() => {
    if (!effectiveDisasterId) return null
    return (
      disasterCache[effectiveDisasterId] ||
      disasters.find((disaster) => String(disaster.id) === effectiveDisasterId) ||
      null
    )
  }, [effectiveDisasterId, disasterCache, disasters])

  const [advisoryZoneId, setAdvisoryZoneId] = useState(null)

  useEffect(() => {
    if (!effectiveDisasterId) {
      setAdvisoryZoneId(null)
      return undefined
    }
    let cancelled = false
    getDisasterZoneAdvisory(Number(effectiveDisasterId), { limit: 1 })
      .then((payload) => {
        if (!cancelled) {
          setAdvisoryZoneId(payload.advisories?.[0]?.zone_id ?? null)
        }
      })
      .catch(() => {
        if (!cancelled) setAdvisoryZoneId(null)
      })
    return () => {
      cancelled = true
    }
  }, [effectiveDisasterId])

  const insightZone = useMemo(() => {
    if (effectiveDisasterId && selectedDisaster) {
      if (advisoryZoneId) {
        const advisoryZone = zones.find((zone) => zone.id === advisoryZoneId)
        if (advisoryZone) return advisoryZone
      }
      return resolveZoneForDisaster(selectedDisaster, zones)
    }
    return pickFallbackInsightZone(zones)
  }, [effectiveDisasterId, selectedDisaster, advisoryZoneId, zones])

  useEffect(() => {
    if (!insightZone?.id) return undefined
    let cancelled = false
    setAiInsight((prev) => ({ ...prev, loading: true, error: "", zoneName: insightZone.zone_name }))
    predictZoneDemand(insightZone.id)
      .then((data) => {
        if (!cancelled) {
          setAiInsight({ loading: false, error: "", data, zoneName: insightZone.zone_name })
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setAiInsight({
            loading: false,
            error: err.message || "Prediction unavailable",
            data: null,
            zoneName: insightZone.zone_name,
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [insightZone?.id, insightZone?.zone_name])

  const topDemandRows = useMemo(() => {
    const estimates = aiInsight.data?.resource_estimates
    if (!estimates) return []
    return Object.entries(estimates)
      .map(([target, payload]) => ({
        target,
        label: targetLabels[target] || target.replace(/_/g, " "),
        demand: Math.ceil(payload?.point_estimate || 0),
      }))
      .filter((row) => row.demand > 0)
      .sort((a, b) => b.demand - a.demand)
      .slice(0, 3)
  }, [aiInsight.data, targetLabels])

  useEffect(() => {
    if (!effectiveDisasterId) return undefined
    let cancelled = false
    getDisaster(Number(effectiveDisasterId))
      .then((data) => {
        if (!cancelled) {
          setDisasterCache((prev) => ({ ...prev, [effectiveDisasterId]: data }))
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [effectiveDisasterId])

  const fetchedDisaster = selectedDisaster

  const zoneMap = useMemo(
    () => Object.fromEntries(zones.map((z) => [z.id, z.zone_name])),
    [zones],
  )

  const chartData = useMemo(() => {
    const grouped = {}
    inventory.forEach((item) => {
      const key = String(item.category || "other").toLowerCase()
      grouped[key] = (grouped[key] || 0) + item.quantity
    })
    const rows = Object.entries(grouped).map(([name, units]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      units,
    }))
    const max = rows.reduce((acc, row) => Math.max(acc, row.units), 0)
    return rows.map((row) => ({
      ...row,
      severity: stockSeverity(max > 0 ? row.units / max : 0),
    }))
  }, [inventory])

  const mapDisasters = useMemo(
    () => pickMapDisasters(disasters, effectiveDisasterId, 120),
    [disasters, effectiveDisasterId],
  )

  function handleDisasterSelect(disasterId) {
    const id = Number(disasterId)
    const disaster =
      disasterCache[String(id)] ||
      disasters.find((item) => Number(item.id) === id)
    const params = { disasterId: String(id) }
    if (disaster?.latitude != null && disaster?.longitude != null) {
      params.lat = String(disaster.latitude)
      params.lon = String(disaster.longitude)
      params.zoom = "10"
    }
    setSearchParams(params)
  }

  const coverageRatio = useMemo(() => {
    if (!metrics) return null
    const allocated = metrics.allocated_resources ?? 0
    const unmet = metrics.unmet_demand ?? 0
    const total = allocated + unmet
    if (total <= 0) return null
    return (allocated / total) * 100
  }, [metrics])

  const criticalZones = metrics?.critical_zones ?? 0

  const coverageTone =
    coverageRatio == null
      ? undefined
      : coverageRatio < 50
        ? "text-[var(--severity-critical-text)]"
        : coverageRatio < 80
          ? "text-[var(--severity-moderate-text)]"
          : "text-[var(--severity-ok-text)]"

  const kpis = (
    <div data-testid="kpi-grid" className="grid grid-cols-2 gap-1.5 md:grid-cols-4">
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
        value={loading ? "—" : String(criticalZones)}
        icon={TriangleAlert}
        description="Commander priority critical"
        severity={criticalZones > 0 ? "critical" : "ok"}
        onClick={() => navigate("/zones?priority=Critical")}
      />
    </div>
  )

  const summary = (
    <div className="ops-card flex max-h-[calc(60vh-1rem)] min-w-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-[var(--border)] p-2">
        <h2 className="mb-2 ops-section-label">
          Operational Summary
        </h2>
        {disasters.length > 0 && (
          <Select
            className="w-full"
            value={effectiveDisasterId ?? ""}
            onChange={(e) => handleDisasterSelect(Number(e.target.value))}
            aria-label="Select incident"
          >
            {disasters.map((disaster) => (
              <option key={disaster.id} value={disaster.id}>
                {disaster.title || formatDisasterType(disaster.disaster_type)} (#{disaster.id})
              </option>
            ))}
          </Select>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
      {fetchedDisaster ? (
        <div className="mb-1.5 border-b border-[var(--border)] pb-1.5">
          <p className="break-words font-semibold leading-snug">
            {fetchedDisaster.title || formatDisasterType(fetchedDisaster.disaster_type)}
          </p>
          <p className="break-words leading-snug text-[var(--text-secondary)]">
            {formatDisasterType(fetchedDisaster.disaster_type)} ·{" "}
            {fetchedDisaster.location || "—"} · {fetchedDisaster.status}
          </p>
          <div className="mt-1">
            <Badge variant={severityBadge(fetchedDisaster.severity)}>
              {fetchedDisaster.severity || "Not rated"}
            </Badge>
          </div>
        </div>
      ) : (
        <p className="mb-1.5 border-b border-[var(--border)] pb-1.5 leading-tight text-[var(--text-secondary)]">
          Select a marker to inspect an incident.
        </p>
      )}

      {metrics && (
        <>
          <SummaryRow label="Allocated" value={metrics.allocated_resources?.toLocaleString() ?? "—"} />
          <SummaryRow label="Reserved" value={(metrics.reserved_resources ?? 0).toLocaleString()} />
          <SummaryRow label="In transit" value={(metrics.in_transit_resources ?? 0).toLocaleString()} />
          <SummaryRow
            label="Coverage"
            value={coverageRatio != null ? `${coverageRatio.toFixed(1)}%` : "—"}
            tone={coverageTone}
            tooltip="Share of total relief demand fulfilled by the latest allocation run (allocated ÷ allocated + unmet)."
          />
          <SummaryRow
            label="Unmet demand"
            value={(metrics.unmet_demand ?? 0).toLocaleString()}
            tone={
              (metrics.unmet_demand ?? 0) > 0
                ? "text-[var(--severity-high-text)]"
                : undefined
            }
            tooltip="Resource units still needed after the most recent optimization — demand minus what depots could allocate."
          />
          <button
            type="button"
            className="mt-1.5 w-full rounded border border-[var(--border)] px-2 py-1 text-left ops-section-label transition-colors hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--focus-ring)]"
            onClick={() => navigate("/missions")}
          >
            Active missions: {metrics.active_missions}
          </button>
          {fetchedDisaster?.id && (
            <div className="mt-2 flex flex-col items-start gap-1.5">
              <DownloadReportButton disasterId={fetchedDisaster.id} />
              <button
                type="button"
                className="w-full rounded border border-[var(--border)] px-2 py-1 text-left ops-section-label transition-colors hover:bg-[var(--surface-hover)]"
                onClick={() => navigate(`/reports/disaster/${fetchedDisaster.id}`)}
              >
                Open situation report
              </button>
            </div>
          )}
        </>
      )}
      </div>
    </div>
  )

  return (
    <div className="space-y-2">
      <PageHeader
        title="Disaster Response Command Center"
        subtitle="Operational overview from live backend data and ML demand signals"
      />

      <div className="ops-card flex flex-wrap items-center justify-between gap-2 p-3" data-testid="ai-demand-insight">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="ops-section-title">AI Predicted Demand</h2>
            <AiEngineLabel title="Point estimates from the zone demand ML model used by the allocation engine.">
              ML model
            </AiEngineLabel>
          </div>
          <p className="ops-muted">
            {aiInsight.zoneName
              ? `Top needs for ${aiInsight.zoneName}`
              : "Loading zone context…"}
            {aiInsight.data?.model_version ? ` · ${aiInsight.data.model_version}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {aiInsight.loading && (
            <span className="ops-muted">Loading prediction…</span>
          )}
          {!aiInsight.loading && aiInsight.error && (
            <span className="ops-muted text-[var(--text-secondary)]">{aiInsight.error}</span>
          )}
          {!aiInsight.loading && !aiInsight.error && topDemandRows.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {topDemandRows.map((row) => (
                <li
                  key={row.target}
                  className="rounded-md border border-[var(--border)] bg-[var(--surface-elevated)] px-2.5 py-1 tabular-nums"
                >
                  <span className="text-[var(--text-secondary)]">{row.label}: </span>
                  <span className="font-semibold">{row.demand.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--accent-text)]"
            onClick={() => navigate("/ai-demand")}
          >
            Full AI Demand
          </button>
        </div>
      </div>

      {/* Map is the primary surface but bounded (~60vh) so Inventory/Missions
          below remain reachable by normal page scroll. */}
      <section className="relative h-[58vh] min-h-[300px] max-h-[620px] w-full">
        <div className="ops-map-surface ops-map-hud-offset relative h-full w-full">
          <DisasterMap
            variant="bleed"
            showIncidentSelect={false}
            disasters={disasters}
            mapDisasters={mapDisasters}
            selectedDisasterId={effectiveDisasterId ? Number(effectiveDisasterId) : null}
            onDisasterSelect={handleDisasterSelect}
            focusLat={focusLat}
            focusLon={focusLon}
            focusZoom={focusZoom}
          />
        </div>

        <div className="ops-hud pointer-events-none absolute inset-0 flex items-start justify-between gap-2 p-2">
          <div className="min-w-0 pointer-events-auto max-w-[calc(100%-20rem)] flex-1">
            {kpis}
          </div>
          <div className="pointer-events-auto w-[19rem] shrink-0">{summary}</div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-2 lg:grid-cols-2 lg:items-stretch">
        <div className="ops-card flex h-full min-h-[14rem] flex-col p-2 lg:min-h-[16rem]">
          <div className="mb-1 flex shrink-0 items-baseline justify-between gap-2">
            <h2 className="ops-section-label">
              Inventory by Category
            </h2>
            <span className="text-[var(--text-secondary)]">
              colour = relative stock level
            </span>
          </div>
          <div className="min-h-0 flex-1">
            <ResourceChart data={chartData} />
          </div>
        </div>

        <div className="ops-card p-2">
          <h2 className="mb-1 text-[0.6875rem] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Recent Missions
          </h2>
          {missions.length === 0 ? (
            <p className="ops-muted">No missions yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="ops-table w-full min-w-[28rem]">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left">
                    <th className="py-1">Code</th>
                    <th className="py-1">Zone</th>
                    <th className="py-1">Priority</th>
                    <th className="py-1">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {missions.slice(0, 6).map((mission) => (
                    <tr key={mission.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="py-1 font-mono">{mission.mission_code}</td>
                      <td className="py-1">{zoneMap[mission.zone_id] || mission.zone_id}</td>
                      <td className="py-1">
                        <Badge variant={severityBadge(mission.priority)}>{mission.priority}</Badge>
                      </td>
                      <td className="py-1">{mission.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
