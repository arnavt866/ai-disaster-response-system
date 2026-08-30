const SEVERITY_ORDER = ["critical", "high", "moderate", "medium", "low"];

export function formatDisasterType(type) {
  if (!type) return "Unknown";
  const labels = {
    EQ: "Earthquake",
    FL: "Flood",
    TC: "Tropical Cyclone",
    WF: "Wildfire",
    DR: "Drought",
    Earthquake: "Earthquake",
  };
  return labels[type] || type;
}

export function normalizeSeverity(severity) {
  if (!severity) return "unknown";
  return String(severity).trim().toLowerCase();
}

export function getSeverityLabel(severity) {
  const value = normalizeSeverity(severity);
  if (!value || value === "unknown") return "Not rated";
  if (value === "medium") return "Moderate";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function getSeverityVariant(severity) {
  const value = normalizeSeverity(severity);
  if (value === "critical") return "critical";
  if (value === "high") return "high";
  if (value === "moderate" || value === "medium") return "medium";
  if (value === "low") return "low";
  return "neutral";
}

export function matchesSeverityFilter(severity, filter) {
  if (filter === "All") return true;
  return normalizeSeverity(severity) === normalizeSeverity(filter);
}

export function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) =>
    String(a).localeCompare(String(b)),
  );
}

export function uniqueSeverities(disasters) {
  const found = disasters
    .map((d) => getSeverityLabel(d.severity))
    .filter((label) => label !== "Not rated");
  return uniqueSorted(found).sort((a, b) => {
    const ai = SEVERITY_ORDER.indexOf(a.toLowerCase());
    const bi = SEVERITY_ORDER.indexOf(b.toLowerCase());
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
}

export function formatEventTime(eventTime) {
  if (!eventTime) return "—";
  const date = new Date(eventTime);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
