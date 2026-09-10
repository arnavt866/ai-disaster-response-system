import { useEffect, useState } from "react"
import { getSatelliteDamage } from "../api/satellite"
import PageHeader from "../components/ui/PageHeader"
import Badge from "../components/ui/Badge"
import { ErrorState } from "../components/ui/StateMessage"
import InfoTooltip from "../components/ui/InfoTooltip"

const PRESETS = [
  { label: "Chennai (demo region)", lat: 13.0827, lon: 80.2707 },
  { label: "Bhubaneswar (demo region)", lat: 20.2961, lon: 85.8245 },
  { label: "Delhi (demo region)", lat: 28.6139, lon: 77.2090 },
]

export default function Satellite() {
  const [latitude, setLatitude] = useState(String(PRESETS[0].lat))
  const [longitude, setLongitude] = useState(String(PRESETS[0].lon))
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    handleLookup(PRESETS[0].lat, PRESETS[0].lon)
  }, [])

  async function handleLookup(lat, lon) {
    setLoading(true)
    setError("")
    try {
      const data = await getSatelliteDamage(lat, lon)
      setResult(data)
    } catch (err) {
      setError(err.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    const lat = Number(latitude)
    const lon = Number(longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      setError("Latitude and longitude must be valid numbers.")
      return
    }
    handleLookup(lat, lon)
  }

  const bestScene = result?.best_scene || result?.scene_metadata?.best_scene
  const previewUrl = result?.preview_url || bestScene?.preview_url

  return (
    <div className="space-y-3">
      <PageHeader
        title="Satellite Imagery"
        subtitle="Sentinel-2 STAC catalog lookup — preview only, no automated damage detection"
      />

      <div className="ops-card p-3">
        <form className="grid grid-cols-1 gap-2 md:grid-cols-4" onSubmit={handleSubmit}>
          <label className="block">
            Latitude
            <input
              className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"
              value={latitude}
              onChange={(e) => setLatitude(e.target.value)}
            />
          </label>
          <label className="block">
            Longitude
            <input
              className="mt-1 block w-full rounded border border-[var(--border)] bg-transparent px-2 py-1"
              value={longitude}
              onChange={(e) => setLongitude(e.target.value)}
            />
          </label>
          <div className="flex items-end">
            <button type="submit" className="ops-btn ops-btn-primary" disabled={loading}>
              {loading ? "Loading…" : "Lookup scene"}
            </button>
          </div>
        </form>
        <div className="mt-2 flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className="ops-btn bg-[var(--surface-elevated)] border border-[var(--border)]"
              onClick={() => {
                setLatitude(String(preset.lat))
                setLongitude(String(preset.lon))
                handleLookup(preset.lat, preset.lon)
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorState title="Satellite lookup failed" message={error} />}

      {result && (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="ops-card p-3">
            <h2 className="mb-2 ops-section-title">Assessment</h2>
            <dl className="space-y-1">
              <div className="flex justify-between gap-2">
                <dt className="inline-flex items-center text-[var(--text-muted)]">
                  Damage level
                  <InfoTooltip
                    label="About damage level"
                    text={'"Unknown" means no automated damage classifier ran on this scene — imagery may still be available. It is not the same as missing coordinates or failed lookup.'}
                  />
                </dt>
                <dd>
                  <Badge variant={result.damage_level === "Unknown" ? "neutral" : "warning"}>
                    {result.damage_level}
                  </Badge>
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--text-muted)]">Status</dt>
                <dd className="text-right">{result.status}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--text-muted)]">Imagery available</dt>
                <dd>{result.imagery_available ? "Yes" : "No"}</dd>
              </div>
            </dl>
          </div>

          <div className="ops-card p-3">
            <h2 className="mb-2 ops-section-title">Scene preview</h2>
            {previewUrl ? (
              <div className="space-y-2">
                <img
                  src={previewUrl}
                  alt="Sentinel-2 scene preview"
                  className="max-h-72 w-full rounded-md border border-[var(--border)] object-contain bg-black/5"
                />
                {bestScene && (
                  <dl className="grid grid-cols-2 gap-x-2 gap-y-1">
                    <dt className="text-[var(--text-muted)]">Scene ID</dt>
                    <dd className="truncate">{bestScene.scene_id}</dd>
                    <dt className="text-[var(--text-muted)]">Datetime</dt>
                    <dd>{bestScene.datetime || "—"}</dd>
                    <dt className="text-[var(--text-muted)]">Cloud cover</dt>
                    <dd>{bestScene.cloud_cover_percent ?? "—"}%</dd>
                    <dt className="text-[var(--text-muted)]">Preview asset</dt>
                    <dd>{result.preview_asset || bestScene.preview_asset || "—"}</dd>
                  </dl>
                )}
              </div>
            ) : (
              <p className="ops-muted">
                No preview asset returned for this location (STAC metadata only).
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
