import { apiRequest } from "./client";

export const getDashboardMetrics = () => apiRequest("/analytics/dashboard");
