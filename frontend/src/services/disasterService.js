import { getDisaster, estimateImpact, getDisasters } from "../api/disasters";

export { getDisasters, getDisaster, estimateImpact };

/** @deprecated Use estimateImpact with disaster coordinates instead. */
export async function getDisasterImpact(disasterId) {
  const disaster = await getDisaster(disasterId);
  return estimateImpact({
    latitude: disaster.latitude,
    longitude: disaster.longitude,
    disaster_type: disaster.disaster_type,
    magnitude: disaster.magnitude ?? 5,
  });
}
