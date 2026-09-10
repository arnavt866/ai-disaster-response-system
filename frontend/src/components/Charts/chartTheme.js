export const CHART_TOOLTIP = {
  backgroundColor: "var(--surface-elevated)",
  color: "var(--text-primary)",
  border: "1px solid var(--border)",
  borderRadius: "6px",
  fontSize: "13px",
}

export const AXIS_TICK = { fontSize: 12, fill: "currentColor" }

export const CATEGORY_COLORS = {
  food: "var(--accent)",
  water: "#0891b2",
  medical: "var(--severity-critical)",
  shelter: "var(--severity-moderate)",
}

export const PRIORITY_COLORS = {
  Critical: "var(--severity-critical)",
  High: "var(--severity-high)",
  Moderate: "var(--severity-moderate)",
  Low: "var(--severity-ok)",
  Unknown: "var(--text-secondary)",
}

export function categoryFill(name) {
  return CATEGORY_COLORS[String(name || "").toLowerCase()] || "var(--accent)"
}

export function priorityFill(name) {
  return PRIORITY_COLORS[name] || "var(--text-secondary)"
}
