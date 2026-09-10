export default function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">{title}</h1>
        {subtitle && (
          <p className="mt-1 ops-muted">{subtitle}</p>
        )}
      </div>
      {actions}
    </div>
  );
}
