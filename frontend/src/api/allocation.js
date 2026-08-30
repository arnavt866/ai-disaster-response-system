import { apiRequest } from "./client";

export const getAllocationStatus = () => apiRequest("/allocation/status");
export const runAllocation = (zoneIds = null, persist = true) =>
  apiRequest("/allocation/optimize", {
    method: "POST",
    body: JSON.stringify({ zone_ids: zoneIds, persist }),
  });
export const recalculateZoneAllocation = (zoneId) =>
  apiRequest(`/allocation/zones/${zoneId}/recalculate`, { method: "POST" });
export const getAllocationHistory = () => apiRequest("/allocation/history");
export const computeRoute = (reliefCenterId, zoneId, blocked = false) =>
  apiRequest("/allocation/route", {
    method: "POST",
    body: JSON.stringify({
      relief_center_id: reliefCenterId,
      zone_id: zoneId,
      blocked,
    }),
  });
