import InfoTooltip from "../ui/InfoTooltip"

const CHIP = {
  critical: "ops-icon-chip--critical",
  high: "ops-icon-chip--high",
  moderate: "ops-icon-chip--moderate",
  ok: "ops-icon-chip--ok",
}

const VALUE_COLOR = {
  critical: "text-[var(--severity-critical-text)]",
  high: "text-[var(--severity-high-text)]",
  moderate: "text-[var(--severity-moderate-text)]",
  ok: "text-[var(--text-primary)]",
}

function StatCard({ title, value, icon: Icon, description, onClick, tooltip, severity }) {
  const clickable = Boolean(onClick)

  return (
    <div
      className={`ops-card px-2.5 py-2 ${clickable ? "ops-card-hover cursor-pointer" : ""}`}
      onClick={onClick}
      onKeyDown={clickable ? (e) => e.key === "Enter" && onClick?.() : undefined}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="inline-flex min-w-0 items-center ops-section-label">
          <span className="truncate" title={title}>
            {title}
          </span>
          {tooltip && <InfoTooltip text={tooltip} label={`About ${title}`} />}
        </p>
        <div
          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded ops-icon-chip ${
            severity ? CHIP[severity] || "" : ""
          }`}
        >
          <Icon className="h-3.5 w-3.5" />
        </div>
      </div>

      <div className="mt-0.5 flex items-baseline gap-1.5">
        <span
          data-testid="stat-value"
          className={`text-[1.5rem] font-semibold leading-none tabular-nums ${
            (severity && VALUE_COLOR[severity]) || "text-[var(--text-primary)]"
          }`}
        >
          {value}
        </span>
      </div>

      {description && (
        <p className="mt-0.5 truncate text-[var(--font-size-sm)] leading-tight text-[var(--text-secondary)]">
          {description}
        </p>
      )}
    </div>
  )
}

export default StatCard
