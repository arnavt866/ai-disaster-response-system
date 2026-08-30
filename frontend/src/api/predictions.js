import { apiRequest } from "./client";

export const predictZoneDemand = (zoneId) =>
  apiRequest(`/prediction/demand/zone/${zoneId}`, { method: "POST" });

export const runScenario = (payload) =>
  apiRequest("/prediction/scenario", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getModelInfo = () => apiRequest("/prediction/model");
