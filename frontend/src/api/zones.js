import { apiRequest } from "./client";

export const getZones = () => apiRequest("/zones/");
export const getZone = (id) => apiRequest(`/zones/${id}`);
export const updateZonePriority = (zoneId, priority) =>
  apiRequest(`/allocation/zones/${zoneId}/priority`, {
    method: "POST",
    body: JSON.stringify({ priority }),
  });
