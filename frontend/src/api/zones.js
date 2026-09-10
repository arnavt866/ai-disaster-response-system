import { apiRequest } from "./client";

function listPath(path, { offset = 0, limit = 5000 } = {}) {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  return `${path}?${params.toString()}`;
}

export async function getZones(options) {
  const body = await apiRequest(listPath("/zones/", options));
  return Array.isArray(body) ? body : body.records;
}

export const getZone = (id) => apiRequest(`/zones/${id}`);
export const updateZonePriority = (zoneId, priority) =>
  apiRequest(`/allocation/zones/${zoneId}/priority`, {
    method: "POST",
    body: JSON.stringify({ priority }),
  });
