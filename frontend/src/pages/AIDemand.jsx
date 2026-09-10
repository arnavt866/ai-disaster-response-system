import { useEffect, useMemo, useState } from "react"
import { getZones } from "../api/zones"
import { predictZoneDemand, runScenario } from "../api/predictions"
import { getInventory } from "../api/inventory"
import { demandTargetMaps, getSystemMetadata } from "../api/system"
import PageHeader from "../components/ui/PageHeader"
import Select from "../components/ui/Select"
import Badge from "../components/ui/Badge"
import { ErrorState } from "../components/ui/StateMessage"
import InfoTooltip from "../components/ui/InfoTooltip"

const CONFORMAL_INTERVAL_TOOLTIP =
  "90% conformal interval: a calibrated range where the true demand should fall about 90% of the time, based on past prediction errors."

export default function AIDemand() {
  const [zones, setZones] = useState([])
  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const [inventory, setInventory] = useState([])
  const [targetLabels, setTargetLabels] = useState({})
  const [categoryForTarget, setCategoryForTarget] = useState({})
  const [zonesLoading, setZonesLoading] = useState(true)
  const [zonesError, setZonesError] = useState("")
  const [fetchState, setFetchState] = useState({
    zoneId: null,
    loading: false,
    error: "",
    data: null,
  })
  const [severityMultiplier, setSeverityMultiplier] = useState("1.5")
  const [scenarioState, setScenarioState] = useState({
    loading: false,
    error: "",
    data: null,
  })

  useEffect(() => {
    let cancelled = false
    Promise.all([getZones(), getInventory(), getSystemMetadata()])
      .then(([zoneData, stock, metadata]) => {
        if (cancelled) return
        setZones(zoneData)
        setInventory(stock)
        const { labels, categories } = demandTargetMaps(metadata)
        setTargetLabels(labels)
        setCategoryForTarget(categories)
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
    setFetchState({ zoneId: selectedZoneId, loading: true, error: "", data: null })
    setScenarioState({ loading: false, error: "", data: null })
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

  async function handleRunScenario(event) {
    event.preventDefault()
    if (!prediction?.features) {
      setScenarioState({
        loading: false,
        error: "Zone feature vector is not available for scenario simulation.",
        data: null,
      })
      return
    }

    const multiplier = Number(severityMultiplier)
    if (!Number.isFinite(multiplier) || multiplier <= 0 || multiplier > 10) {
      setScenarioState({
        loading: false,
        error: "Severity multiplier must be between 0 and 10.",
        data: null,
      })
      return
    }

    setScenarioState({ loading: true, error: "", data: null })
    try {
      const result = await runScenario({
        features: prediction.features,
        severity_multiplier: multiplier,
        response_speed_factor: 1.0,
        resource_availability_factor: 1.0,
      })
      setScenarioState({ loading: false, error: "", data: result })
    } catch (err) {
      setScenarioState({ loading: false, error: err.message, data: null })
    }
  }

  const scenarioRows = useMemo(() => {
    if (!prediction?.resource_estimates || !scenarioState.data?.predictions) {
      return []
    }
    return Object.entries(prediction.resource_estimates).map(([target, baseline]) => {
      const scenario = scenarioState.data.predictions[target] || {}
      const baselineDemand = Math.ceil(baseline.point_estimate || 0)
      const adjustedDemand = Math.ceil(scenario.scenario_adjusted_estimate || 0)
      return {
        target,
        baselineDemand,
        adjustedDemand,
        delta: adjustedDemand - baselineDemand,
      }
    })
  }, [prediction, scenarioState.data])

  if (zonesLoading) {
    return (
      <div className="space-y-2">
        <PageHeader title="AI Demand Prediction" subtitle="M2 model demand by zone (proxy targets)" />
        <p className="ops-muted">Loading zones...</p>
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
        <label className="ops-muted">Zone</label>
        <Select className="max-w-md" value={selectedZoneId ?? ""} onChange={handleZoneChange}>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>{zone.zone_name}</option>
          ))}
        </Select>
      </div>

      {zonesError && <ErrorState title="Unable to load zones" message={zonesError} />}
      {predictionError && <ErrorState title="Unable to load prediction" message={predictionError} />}
      {predictionLoading && <p className="ops-muted">Loading prediction...</p>}

      {prediction && !predictionError && (
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-3">
          <div className="ops-card p-2 lg:col-span-1">
            <h2 className="mb-2 ops-section-title">Zone Context</h2>
            <dl className="space-y-1">
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Type</dt><dd>{prediction.disaster_type || "—"}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Severity</dt><dd>{prediction.severity || "—"}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Population</dt><dd>{prediction.milestone1_grid_analysis?.estimated_population ?? "—"}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-[var(--text-muted)]">Model</dt><dd>{prediction.model_version || "—"}</dd></div>
              {prediction.vulnerability && (
                <div className="flex justify-between gap-2">
                  <dt className="inline-flex items-center text-[var(--text-muted)]">
                    Vulnerability factor
                    <InfoTooltip
                      label="About vulnerability factor"
                      text="Demand multiplier from zone demographics: higher elderly and children shares increase estimated need (weights 15% and 10%). Neutral 1.0 when census data is unavailable."
                    />
                  </dt>
                  <dd>{prediction.vulnerability.vulnerability_factor ?? "—"}</dd>
                </div>
              )}
            </dl>
            <p className="mt-2 ops-muted">
              Proxy demand only — not observed consumption.
            </p>
          </div>

          <div className="ops-card overflow-x-auto p-2 lg:col-span-2">
            {estimateEntries.length === 0 ? (
              <p className="p-4 ops-muted">
                No demand prediction is available for this zone.
                {prediction.target_method ? ` (${prediction.target_method})` : ""}
              </p>
            ) : (
              <table className="ops-table min-w-full">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left">
                    <th >Resource</th>
                    <th >Predicted Demand</th>
                    <th >
                      <span className="inline-flex items-center">
                        Lower 90%
                        <InfoTooltip label="About lower 90% interval" text={CONFORMAL_INTERVAL_TOOLTIP} />
                      </span>
                    </th>
                    <th >
                      <span className="inline-flex items-center">
                        Upper 90%
                        <InfoTooltip label="About upper 90% interval" text={CONFORMAL_INTERVAL_TOOLTIP} />
                      </span>
                    </th>
                    <th >Availability</th>
                    <th >Coverage</th>
                    <th >Status</th>
                  </tr>
                </thead>
                <tbody>
                  {estimateEntries.map(([target, payload]) => {
                    const category = categoryForTarget[target]
                    const available = availabilityByCategory[category] ?? 0
                    const demand = Math.ceil(payload.point_estimate || 0)
                    const coverage = demand > 0 ? Math.min(100, (available / demand) * 100) : 100
                    const status = coverage >= 100 ? "Covered" : coverage >= 50 ? "Partial" : "Critical gap"

                    return (
                      <tr key={target} className="border-b border-[var(--border)]">
                        <td className="font-medium">{targetLabels[target] || target}</td>
                        <td >{demand.toLocaleString()}</td>
                        <td >{Math.ceil(payload.prediction_interval_lower || 0).toLocaleString()}</td>
                        <td >{Math.ceil(payload.prediction_interval_upper || 0).toLocaleString()}</td>
                        <td >{available.toLocaleString()}</td>
                        <td >{coverage.toFixed(0)}%</td>
                        <td >
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

      {prediction && !predictionError && (
        <div className="ops-card space-y-2 p-2">
          <h2 className="ops-section-title">Scenario Simulation</h2>
          <p className="ops-muted">
            Scale proxy demand using <code>/prediction/scenario</code> multipliers (baseline vs adjusted).
          </p>
          <form className="flex flex-wrap items-end gap-2" onSubmit={handleRunScenario}>
            <label className="ops-muted">
              Severity multiplier
              <input
                className="mt-1 block w-28 rounded border border-[var(--border)] bg-transparent px-2 py-1"
                type="number"
                min="0.1"
                max="10"
                step="0.1"
                value={severityMultiplier}
                onChange={(event) => setSeverityMultiplier(event.target.value)}
              />
            </label>
            <button
              type="submit"
              className="ops-btn ops-btn-primary"
              disabled={scenarioState.loading || !prediction.features}
            >
              {scenarioState.loading ? "Running..." : "Run scenario"}
            </button>
          </form>
          {scenarioState.error && (
            <ErrorState title="Scenario simulation failed" message={scenarioState.error} />
          )}
          {scenarioState.data && scenarioRows.length > 0 && (
            <div className="overflow-x-auto">
              <table className="ops-table min-w-full">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left">
                    <th >Resource</th>
                    <th >Baseline demand</th>
                    <th >Scenario adjusted</th>
                    <th >Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarioRows.map((row) => (
                    <tr key={row.target} className="border-b border-[var(--border)]">
                      <td className="font-medium">{targetLabels[row.target] || row.target}</td>
                      <td >{row.baselineDemand.toLocaleString()}</td>
                      <td >{row.adjustedDemand.toLocaleString()}</td>
                      <td >
                        <Badge variant={row.delta > 0 ? "warning" : row.delta < 0 ? "success" : "neutral"}>
                          {row.delta > 0 ? "+" : ""}{row.delta.toLocaleString()}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 ops-muted">
                Effective severity multiplier:{" "}
                {scenarioState.data.scenario_parameters?.effective_severity_multiplier ?? "—"}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
