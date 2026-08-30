import { apiRequest } from "./client";

export const getDisasters = () => apiRequest("/disasters/");
export const getDisaster = (id) => apiRequest(`/disasters/${id}`);

export const estimateImpact = (params) => {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/impact/estimate?${query}`);
};
