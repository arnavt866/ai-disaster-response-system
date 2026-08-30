const VARIANTS = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
  success: "badge-success",
  warning: "badge-warning",
  neutral: "badge-neutral",
  info: "badge-info",
};

export default function Badge({ children, variant = "neutral", className = "" }) {
  return (
    <span className={`ops-badge ${VARIANTS[variant] || VARIANTS.neutral} ${className}`}>
      {children}
    </span>
  );
}
