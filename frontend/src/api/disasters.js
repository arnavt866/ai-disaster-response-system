import { apiRequest } from "./client";

function listPath(path, { offset = 0, limit = 5000 } = {}) {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  return `${path}?${params.toString()}`;
}

export async function getDisasters(options) {
  const body = await apiRequest(listPath("/disasters/", options));
  return Array.isArray(body) ? body : body.records;
}

export const getDisaster = (id) => apiRequest(`/disasters/${id}`);

export const estimateImpact = (params) => {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/impact/estimate?${query}`);
};

export const getDisasterZoneAdvisory = (disasterId, { radiusKm = 150, limit = 12 } = {}) => {
  const params = new URLSearchParams({
    radius_km: String(radiusKm),
    limit: String(limit),
  });
  return apiRequest(`/disasters/${disasterId}/zone-advisory?${params.toString()}`);
};
