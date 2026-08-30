export function severityBadge(severity) {
  const value = String(severity || "").toLowerCase();
  if (value === "critical") return "critical";
  if (value === "high") return "high";
  if (value === "moderate" || value === "medium") return "medium";
  if (value === "low") return "low";
  return "neutral";
}

export function statusBadge(status) {
  const value = String(status || "").toLowerCase();
  if (value === "delivered" || value === "active") return "success";
  if (value === "in transit" || value === "dispatched") return "info";
  if (value === "allocated" || value === "created") return "warning";
  if (value === "inactive" || value === "blocked") return "critical";
  return "neutral";
}
