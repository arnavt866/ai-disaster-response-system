export function LoadingState({ message = "Loading..." }) {
  return (
    <div className="ops-card flex min-h-48 items-center justify-center p-6">
      <div className="text-center">
        <div className="mx-auto h-7 w-7 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--primary)]" />
        <p className="mt-3 text-sm text-[var(--text-muted)]">{message}</p>
      </div>
    </div>
  );
}

export function ErrorState({ title = "Unable to load data", message }) {
  return (
    <div className="ops-card p-6 text-center">
      <h2 className="text-base font-semibold text-[var(--critical)]">{title}</h2>
      {message && <p className="mt-2 text-sm text-[var(--text-muted)]">{message}</p>}
    </div>
  );
}

export function EmptyState({ message = "No records found." }) {
  return (
    <div className="ops-card p-6 text-center">
      <p className="text-sm text-[var(--text-muted)]">{message}</p>
    </div>
  );
}
