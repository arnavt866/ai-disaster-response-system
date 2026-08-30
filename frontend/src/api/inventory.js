import { apiRequest } from "./client";

export const getInventory = () => apiRequest("/inventory/");
export const getReliefCenters = () => apiRequest("/relief-centers/");
