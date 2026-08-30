function StatCard({ title, value, icon: Icon, description, onClick }) {
  const clickable = Boolean(onClick)

  return (
    <div
      className={`ops-card p-3 ${clickable ? "ops-card-hover cursor-pointer" : ""}`}
      onClick={onClick}
      onKeyDown={clickable ? (e) => e.key === "Enter" && onClick?.() : undefined}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-[var(--text-muted)]">{title}</p>
          <h2 className="mt-1 text-2xl font-bold text-[var(--text-primary)]">{value}</h2>
          {description && (
            <p className="mt-1 text-sm text-[var(--text-muted)]">{description}</p>
          )}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md ops-icon-chip">
          <Icon className="h-4 w-4 text-[var(--primary)]" />
        </div>
      </div>
    </div>
  )
}

export default StatCard
