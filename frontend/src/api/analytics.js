import { API_BASE_URL, apiRequest } from "./client";
import { getStoredToken } from "../auth/session";

export const getDashboardMetrics = () => apiRequest("/analytics/dashboard");

export const getAllocationReports = () => apiRequest("/analytics/reports");

export const getSituationReport = (disasterId) =>
  apiRequest(`/analytics/situation-report/${disasterId}`);

export async function downloadSituationReportHtml(disasterId) {
  const headers = {};
  const token = getStoredToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  // bare=true omits the Print / Save as PDF bar entirely, so no export path can
  // bake the button into a PDF even if it ignores @media print. Browser Ctrl+P
  // on the saved file still works.
  const response = await fetch(
    `${API_BASE_URL}/analytics/situation-report/${disasterId}/html?bare=true&t=${Date.now()}`,
    { headers, cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error(`Report download failed: ${response.status}`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] || `DRMS-situation-report-${disasterId}.html`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return filename;
}
