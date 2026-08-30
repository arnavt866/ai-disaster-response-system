import { useEffect, useMemo, useState } from "react"
import { getDisasters, estimateImpact } from "../../api/disasters"
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

function MapUpdater({ latitude, longitude, zoom = 8 }) {
  const map = useMap()
  useEffect(() => {
    if (latitude != null && longitude != null) {
      map.setView([latitude, longitude], zoom, { animate: true })
    }
  }, [latitude, longitude, zoom, map])
  return null
}

function MapResizeHandler({ trigger }) {
  const map = useMap()
  useEffect(() => {
    const timer = setTimeout(() => map.invalidateSize(), 100)
    return () => clearTimeout(timer)
  }, [trigger, map])
  return null
}

function DisasterMap({
  selectedDisasterId: externalDisasterId,
  onDisasterSelect,
  focusLat,
  focusLon,
  focusZoom = 9,
  showFullscreen = true,
}) {
  const [disasters, setDisasters] = useState([])
  const [internalDisasterId, setInternalDisasterId] = useState(null)
  const [impactById, setImpactById] = useState({})
  const [error, setError] = useState("")
  const [disastersLoaded, setDisastersLoaded] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)

  const selectedDisasterId = externalDisasterId ?? internalDisasterId

  useEffect(() => {
    let cancelled = false
    getDisasters()
      .then((data) => {
        if (cancelled) return
        setDisasters(data)
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
  }, [externalDisasterId])

  const selected = useMemo(
    () => disasters.find((item) => item.id === selectedDisasterId),
    [disasters, selectedDisasterId],
  )

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
    return <div className="flex h-full items-center justify-center text-sm text-[var(--text-muted)]">Loading map...</div>
  }

  if (error && disasters.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-4 text-center text-sm text-[var(--text-muted)]">
        {error || "No disasters available. Import GDACS/USGS data or create a disaster event."}
      </div>
    )
  }

  const impact = selected ? impactById[selected.id] : null
  const radiusKm = impact?.impact_radius_km ?? impact?.radius_km ?? 10

  const containerClass = fullscreen
    ? "fixed inset-0 z-50 flex flex-col bg-[var(--bg)] p-2"
    : "flex h-full flex-col"

  return (
    <div className={containerClass}>
      <div className="mb-2 flex items-center gap-2">
        {!externalDisasterId && disasters.length > 0 && (
          <Select
            className="flex-1"
            value={selectedDisasterId ?? ""}
            onChange={(e) => handleSelect(Number(e.target.value))}
          >
            {disasters.map((disaster) => (
              <option key={disaster.id} value={disaster.id}>
                {disaster.title || disaster.disaster_type} (#{disaster.id})
              </option>
            ))}
          </Select>
        )}
        {showFullscreen && (
          <button
            type="button"
            className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--text-primary)]"
            onClick={() => setFullscreen((prev) => !prev)}
            title={fullscreen ? "Exit fullscreen" : "Fullscreen map"}
          >
            {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-[var(--border)]">
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
          />
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {disasters.map((disaster) => (
            <Marker
              key={disaster.id}
              position={[disaster.latitude, disaster.longitude]}
              eventHandlers={{
                click: () => handleSelect(disaster.id),
              }}
              opacity={disaster.id === selectedDisasterId ? 1 : 0.75}
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
                  className="mt-1 text-sm text-[var(--primary)] underline"
                  onClick={() => handleSelect(disaster.id)}
                >
                  Select incident
                </button>
              </Popup>
            </Marker>
          ))}
          {selected && (
            <Circle
              center={[selected.latitude, selected.longitude]}
              radius={radiusKm * 1000}
              pathOptions={{ color: "var(--critical)", fillOpacity: 0.12 }}
            />
          )}
        </MapContainer>
      </div>
    </div>
  )
}

export default DisasterMap
