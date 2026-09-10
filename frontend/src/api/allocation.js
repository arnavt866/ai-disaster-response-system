import { apiRequest } from "./client";

export const getAllocationStatus = () => apiRequest("/allocation/status");
export const runAllocation = (
  zoneIds = null,
  persist = true,
  confirmAllZones = false,
  maxZones = null,
) =>
  apiRequest("/allocation/optimize", {
    method: "POST",
    body: JSON.stringify({
      zone_ids: zoneIds,
      persist,
      confirm_all_zones: confirmAllZones,
      max_zones: maxZones,
    }),
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

export const getRoadBlocks = (regionId = null) => {
  const query = regionId ? `?region_id=${encodeURIComponent(regionId)}` : "";
  return apiRequest(`/allocation/road-blocks${query}`);
};

export const blockRoadSegment = (regionId, u, v) =>
  apiRequest("/allocation/road-blocks", {
    method: "POST",
    body: JSON.stringify({ region_id: regionId, u, v }),
  });

export const unblockRoadSegment = (regionId, u, v) =>
  apiRequest("/allocation/road-blocks", {
    method: "DELETE",
    body: JSON.stringify({ region_id: regionId, u, v }),
  });

export const clearRoadBlocks = (regionId = null) =>
  apiRequest("/allocation/road-blocks/clear", {
    method: "POST",
    body: JSON.stringify({ region_id: regionId }),
  });
