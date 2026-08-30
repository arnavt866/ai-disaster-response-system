import { useEffect, useMemo, useState } from "react"
import { getZones } from "../api/zones"
import { predictZoneDemand } from "../api/predictions"
import { getInventory } from "../api/inventory"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import Badge from "../components/ui/Badge"
import { ErrorState } from "../components/ui/StateMessage"

const TARGET_LABELS = {
  food_packets_demand: "Food",
  water_demand: "Water",
  medical_kits_demand: "Medical",
  shelter_capacity_demand: "Shelter",
}

const CATEGORY_FOR_TARGET = {
  food_packets_demand: "food",
  water_demand: "water",
  medical_kits_demand: "medical",
  shelter_capacity_demand: "shelter",
}

export default function AIDemand() {
  const [zones, setZones] = useState([])
  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const [inventory, setInventory] = useState([])
  const [zonesLoading, setZonesLoading] = useState(true)
  const [zonesError, setZonesError] = useState("")
  const [fetchState, setFetchState] = useState({
    zoneId: null,
    loading: false,
    error: "",
    data: null,
  })

  useEffect(() => {
    let cancelled = false
    Promise.all([getZones(), getInventory()])
      .then(([zoneData, stock]) => {
        if (cancelled) return
        setZones(zoneData)
        setInventory(stock)
        if (zoneData.length > 0) {
          setSelectedZoneId(zoneData[0].id)
        }
      })
      .catch((err) => {
        if (!cancelled) setZonesError(err.message)
      })
      .finally(() => {
        if (!cancelled) setZonesLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!selectedZoneId) return undefined
    let cancelled = false
    predictZoneDemand(selectedZoneId)
      .then((result) => {
        if (!cancelled) {
          setFetchState({ zoneId: selectedZoneId, loading: false, error: "", data: result })
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setFetchState({
            zoneId: selectedZoneId,
            loading: false,
            error: err.message,
            data: null,
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [selectedZoneId])

  const prediction =
    fetchState.zoneId === selectedZoneId ? fetchState.data : null
  const predictionLoading =
    Boolean(selectedZoneId) && fetchState.zoneId !== selectedZoneId && !fetchState.error
  const predictionError =
    fetchState.zoneId === selectedZoneId ? fetchState.error : ""

  const estimates = prediction?.resource_estimates || {}
  const estimateEntries = Object.entries(estimates)

  const availabilityByCategory = useMemo(() => {
    const totals = {}
    inventory.forEach((item) => {
      const key = String(item.category || "").toLowerCase()
      totals[key] = (totals[key] || 0) + (item.quantity || 0)
    })
    return totals
  }, [inventory])

  function handleZoneChange(event) {
    setSelectedZoneId(Number(event.target.value))
  }

  if (zonesLoading) {
    return (
      <div className="space-y-2">
        <PageHeader title="AI Demand Prediction" subtitle="M2 model demand by zone (proxy targets)" />
        <p className="text-sm text-[var(--text-muted)]">Loading zones...</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <PageHeader
        title="AI Demand Prediction"
        subtitle="M2 model demand by zone (proxy targets, target_is_observed=false)"
      />

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-[var(--text-muted)]">Zone</label>
        <Select className="max-w-md" value={selectedZoneId ?? ""} onChange={handleZoneChange}>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>{zone.zone_name}</option>
          ))}
        </Select>
      </div>

      {zonesError && <ErrorState title="Unable to load zones" message={zonesError} />}
      {predictionError && <ErrorState title="Unable to load prediction" message={predictionError} />}
      {predictionLoading && <p className="text-sm text-[var(--text-muted)]">Loading prediction...</p>}

      {prediction && !predictionError && (
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-3">
          <div className="ops-card p-2 lg:col-span-1">
            <h2 className="mb-2 text-sm font-semibold">Zone Context</h2>
            <dl className="space-y-1 text-sm">
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Type</dt><dd>{prediction.disaster_type || "—"}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Severity</dt><dd>{prediction.severity || "—"}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Population</dt><dd>{prediction.milestone1_grid_analysis?.estimated_population ?? "—"}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Model</dt><dd className="text-sm">{prediction.model_version || "—"}</dd></div>
            </dl>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Proxy demand only — not observed consumption.
            </p>
          </div>

          <div className="ops-card overflow-x-auto p-2 lg:col-span-2">
            {estimateEntries.length === 0 ? (
              <p className="p-4 text-sm text-[var(--text-muted)]">
                No demand prediction is available for this zone.
                {prediction.target_method ? ` (${prediction.target_method})` : ""}
              </p>
            ) : (
              <table className="ops-table min-w-full">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left">
                    <th className="px-3 py-2">Resource</th>
                    <th className="px-3 py-2">Predicted Demand</th>
                    <th className="px-3 py-2">Lower 90%</th>
                    <th className="px-3 py-2">Upper 90%</th>
                    <th className="px-3 py-2">Availability</th>
                    <th className="px-3 py-2">Coverage</th>
                    <th className="px-3 py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {estimateEntries.map(([target, payload]) => {
                    const category = CATEGORY_FOR_TARGET[target]
                    const available = availabilityByCategory[category] ?? 0
                    const demand = Math.ceil(payload.point_estimate || 0)
                    const coverage = demand > 0 ? Math.min(100, (available / demand) * 100) : 100
                    const status = coverage >= 100 ? "Covered" : coverage >= 50 ? "Partial" : "Critical gap"

                    return (
                      <tr key={target} className="border-b border-[var(--border)]">
                        <td className="px-3 py-2 font-medium">{TARGET_LABELS[target] || target}</td>
                        <td className="px-3 py-2">{demand.toLocaleString()}</td>
                        <td className="px-3 py-2">{Math.ceil(payload.prediction_interval_lower || 0).toLocaleString()}</td>
                        <td className="px-3 py-2">{Math.ceil(payload.prediction_interval_upper || 0).toLocaleString()}</td>
                        <td className="px-3 py-2">{available.toLocaleString()}</td>
                        <td className="px-3 py-2">{coverage.toFixed(0)}%</td>
                        <td className="px-3 py-2">
                          <Badge variant={status === "Covered" ? "success" : status === "Partial" ? "warning" : "critical"}>
                            {status}
                          </Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
