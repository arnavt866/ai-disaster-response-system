import { haversineKm } from "./routeUtils";
import { formatDisasterType } from "./disasterHelpers";

const PRIORITY_RANK = { Critical: 0, High: 1, Moderate: 2, Low: 3 };

function disasterTypeTokens(type) {
  const label = formatDisasterType(type);
  const raw = String(type || "").trim();
  return new Set([raw, label].map((v) => v.toLowerCase()).filter(Boolean));
}

function zoneMatchesDisasterType(zone, disaster) {
  const zoneTokens = disasterTypeTokens(zone.disaster_type);
  const disasterTokens = disasterTypeTokens(disaster.disaster_type);
  for (const token of disasterTokens) {
    if (zoneTokens.has(token)) return true;
  }
  return false;
}

/** Highest-priority active zone when no incident is selected yet. */
export function pickFallbackInsightZone(zones) {
  if (!zones?.length) return null;
  const active = zones.filter((zone) => zone.status === "Active");
  const pool = active.length > 0 ? active : zones;
  const rank = (zone) =>
    PRIORITY_RANK[zone.operational_priority] ??
    PRIORITY_RANK[zone.severity] ??
    99;
  return [...pool].sort((a, b) => rank(a) - rank(b))[0];
}

/** Nearest active zone to a disaster centroid, preferring matching disaster type. */
export function resolveZoneForDisaster(disaster, zones) {
  if (!disaster || !zones?.length) return null;

  const active = zones.filter((zone) => zone.status === "Active");
  const pool = active.length > 0 ? active : zones;
  const typed = pool.filter((zone) => zoneMatchesDisasterType(zone, disaster));
  const candidates = typed.length > 0 ? typed : pool;

  let best = null;
  let bestDistance = Infinity;
  for (const zone of candidates) {
    const distance = haversineKm(
      disaster.latitude,
      disaster.longitude,
      zone.latitude,
      zone.longitude,
    );
    if (distance < bestDistance) {
      bestDistance = distance;
      best = zone;
    }
  }
  return best;
}
