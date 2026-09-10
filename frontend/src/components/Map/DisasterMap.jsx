import { memo, useEffect, useMemo, useState } from "react"
import { getDisasters, estimateImpact } from "../../api/disasters"
import { pickMapDisasters, sameDisasterId } from "../../utils/mapDisasters"
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from "react-leaflet"
import { Maximize2, Minimize2 } from "lucide-react"
import L from "leaflet"
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png"
import markerIcon from "leaflet/dist/images/marker-icon.png"
import markerShadow from "leaflet/dist/images/marker-shadow.png"
import Select from "../ui/Select"
import "leaflet/dist/leaflet.css"

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

function severityKey(severity) {
  const value = String(severity || "").toLowerCase()
  if (value === "critical") return "critical"
  if (value === "high") return "high"
  if (value === "moderate" || value === "medium") return "moderate"
  if (value === "low") return "ok"
  return "neutral"
}

const SEVERITY_STROKE = {
  critical: "var(--severity-critical)",
  high: "var(--severity-high)",
  moderate: "var(--severity-moderate)",
  ok: "var(--severity-ok)",
  neutral: "var(--text-secondary)",
}

// Severity-coloured pin replaces Leaflet's single default blue marker.
function severityPin(severity, selected) {
  const key = severityKey(severity)
  const size = selected ? 20 : 14
  return L.divIcon({
    className: "ops-map-pin-wrap",
    html: `<span class="ops-map-pin ops-map-pin--${key}${
      selected ? " ops-map-pin--selected" : ""
    }"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2)],
  })
}

function MapUpdater({ latitude, longitude, zoom = 8, focusKey }) {
  const map = useMap()
  useEffect(() => {
    if (latitude != null && longitude != null) {
      map.setView([latitude, longitude], zoom, { animate: true })
    }
  }, [latitude, longitude, zoom, focusKey, map])
  return null
}

const DisasterMarker = memo(function DisasterMarker({
  disaster,
  selected,
  onSelect,
}) {
  return (
    <Marker
      position={[disaster.latitude, disaster.longitude]}
      icon={severityPin(disaster.severity, selected)}
      eventHandlers={{
        click: () => onSelect(disaster.id),
      }}
      opacity={selected ? 1 : 0.85}
    >
      <Popup>
        <strong>{disaster.disaster_type}</strong>
        <br />
        {disaster.location || `${disaster.latitude}, ${disaster.longitude}`}
        <br />
        Severity: {disaster.severity || "Not rated"}
        <br />
        <button
          type="button"
          className="mt-1 text-sm text-[var(--accent-text)] underline"
          onClick={() => onSelect(disaster.id)}
        >
          Select incident
        </button>
      </Popup>
    </Marker>
  )
})

function MapResizeHandler({ trigger }) {
  const map = useMap()
  useEffect(() => {
    const timer = setTimeout(() => map.invalidateSize(), 100)
    return () => clearTimeout(timer)
  }, [trigger, map])
  return null
}

function DisasterMap({
  disasters: externalDisasters,
  mapDisasters: externalMapDisasters,
  mapMarkerLimit = 120,
  selectedDisasterId: externalDisasterId,
  onDisasterSelect,
  focusLat,
  focusLon,
  focusZoom = 9,
  showFullscreen = true,
  variant = "card",
  showIncidentSelect = true,
}) {
  const [fetchedDisasters, setFetchedDisasters] = useState([])
  const [internalDisasterId, setInternalDisasterId] = useState(null)
  const [impactById, setImpactById] = useState({})
  const [error, setError] = useState("")
  const [disastersLoaded, setDisastersLoaded] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)

  const disasters = externalDisasters ?? fetchedDisasters
  const selectedDisasterId = externalDisasterId ?? internalDisasterId

  useEffect(() => {
    if (externalDisasters) {
      setDisastersLoaded(true)
      return undefined
    }

    let cancelled = false
    getDisasters()
      .then((data) => {
        if (cancelled) return
        setFetchedDisasters(data)
        if (!externalDisasterId && data.length > 0) {
          setInternalDisasterId(data[0].id)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setDisastersLoaded(true)
      })
    return () => {
      cancelled = true
    }
  }, [externalDisasters, externalDisasterId])

  const selected = useMemo(
    () => disasters.find((item) => sameDisasterId(item.id, selectedDisasterId)),
    [disasters, selectedDisasterId],
  )

  const markerDisasters = useMemo(() => {
    if (externalMapDisasters) return externalMapDisasters
    return pickMapDisasters(disasters, selectedDisasterId, mapMarkerLimit)
  }, [externalMapDisasters, disasters, selectedDisasterId, mapMarkerLimit])

  const mapCenter = useMemo(() => {
    if (focusLat != null && focusLon != null) return [focusLat, focusLon]
    if (selected) return [selected.latitude, selected.longitude]
    return [20.5937, 78.9629]
  }, [focusLat, focusLon, selected])

  useEffect(() => {
    if (!selected) return undefined
    const disasterId = selected.id
    if (impactById[disasterId]) return undefined

    let cancelled = false
    estimateImpact({
      latitude: selected.latitude,
      longitude: selected.longitude,
      disaster_type: selected.disaster_type,
      magnitude: selected.magnitude ?? 5,
    })
      .then((data) => {
        if (!cancelled) {
          setImpactById((prev) => ({ ...prev, [disasterId]: data }))
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [selected, impactById])

  function handleSelect(disasterId) {
    if (onDisasterSelect) {
      onDisasterSelect(disasterId)
    } else {
      setInternalDisasterId(disasterId)
    }
  }

  if (!disastersLoaded) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-[var(--text-secondary)]">
        Loading map...
      </div>
    )
  }

  if (error && disasters.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-4 text-center text-sm text-[var(--text-secondary)]">
        {error || "No disasters available. Import GDACS/USGS data or create a disaster event."}
      </div>
    )
  }

  const impact = selected ? impactById[selected.id] : null
  const radiusKm = impact?.impact_radius_km ?? impact?.radius_km ?? 10
  const selectedStroke = SEVERITY_STROKE[severityKey(selected?.severity)]

  const incidentSelect =
    showIncidentSelect && disasters.length > 0 ? (
      <Select
        className="min-w-0 flex-1"
        value={selectedDisasterId ?? ""}
        onChange={(e) => handleSelect(Number(e.target.value))}
      >
        {disasters.map((disaster) => (
          <option key={disaster.id} value={disaster.id}>
            {disaster.title || disaster.disaster_type} (#{disaster.id})
          </option>
        ))}
      </Select>
    ) : null

  const fullscreenButton = showFullscreen ? (
    <button
      type="button"
      className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--text-primary)]"
      onClick={() => setFullscreen((prev) => !prev)}
      title={fullscreen ? "Exit fullscreen" : "Fullscreen map"}
    >
      {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
    </button>
  ) : null

  const mapBody = (
    <MapContainer
      center={mapCenter}
      zoom={focusLat != null ? focusZoom : 8}
      className="h-full w-full"
      scrollWheelZoom
      doubleClickZoom
      dragging
      zoomControl
    >
      <MapResizeHandler trigger={fullscreen} />
      <MapUpdater
        latitude={focusLat ?? selected?.latitude}
        longitude={focusLon ?? selected?.longitude}
        zoom={focusZoom}
        focusKey={selectedDisasterId ?? "none"}
      />
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {markerDisasters.map((disaster) => (
        <DisasterMarker
          key={disaster.id}
          disaster={disaster}
          selected={sameDisasterId(disaster.id, selectedDisasterId)}
          onSelect={handleSelect}
        />
      ))}
      {selected && (
        <Circle
          center={[selected.latitude, selected.longitude]}
          radius={radiusKm * 1000}
          pathOptions={{ color: selectedStroke, weight: 2, fillOpacity: 0.1 }}
        />
      )}
    </MapContainer>
  )

  // Full-bleed: the map fills its parent and controls float above it, so no
  // heading/subtitle/dropdown consumes vertical space before the map starts.
  if (variant === "bleed") {
    const shellClass = fullscreen
      ? "fixed inset-0 z-50 flex flex-col bg-[var(--bg)] p-2"
      : "absolute inset-0"
    const frameClass = fullscreen
      ? "ops-map-surface relative min-h-0 flex-1"
      : "relative h-full w-full"

    return (
      <div className={shellClass}>
        <div className={frameClass}>
          {mapBody}
          <div className="pointer-events-none absolute right-2 top-2 z-[500] flex max-w-[calc(100%-1rem)] items-center gap-1.5">
            {incidentSelect && (
              <div className="ops-overlay-panel pointer-events-auto flex min-w-0 max-w-[15rem] items-center p-1">
                {incidentSelect}
              </div>
            )}
            {fullscreenButton && (
              <div className="pointer-events-auto">{fullscreenButton}</div>
            )}
          </div>
        </div>
      </div>
    )
  }

  const containerClass = fullscreen
    ? "fixed inset-0 z-50 flex flex-col bg-[var(--bg)] p-2"
    : "flex h-full flex-col"

  return (
    <div className={containerClass}>
      <div className="mb-2 flex items-center gap-2">
        {incidentSelect}
        {fullscreenButton}
      </div>
      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-[var(--border)]">
        {mapBody}
      </div>
    </div>
  )
}

export default DisasterMap
