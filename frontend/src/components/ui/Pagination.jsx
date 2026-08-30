export default function Pagination({
  page,
  totalPages,
  totalItems,
  rangeStart,
  rangeEnd,
  onPageChange,
  hasPrevious,
  hasNext,
}) {
  if (totalItems === 0) return null;

  const pages = buildPageList(page, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] px-2 py-2 text-sm">
      <p className="text-[var(--text-muted)]">
        Showing {rangeStart}–{rangeEnd} of {totalItems}
      </p>

      <div className="flex items-center gap-1">
        <button
          type="button"
          className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-40"
          onClick={() => onPageChange(page - 1)}
          disabled={!hasPrevious}
        >
          Previous
        </button>

        {pages.map((item, index) =>
          item === "…" ? (
            <span key={`ellipsis-${index}`} className="px-2 text-[var(--text-muted)]">
              …
            </span>
          ) : (
            <button
              key={item}
              type="button"
              className={`ops-btn min-w-8 border ${
                item === page
                  ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                  : "border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--text-primary)]"
              }`}
              onClick={() => onPageChange(item)}
              aria-current={item === page ? "page" : undefined}
            >
              {item}
            </button>
          ),
        )}

        <button
          type="button"
          className="ops-btn border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-40"
          onClick={() => onPageChange(page + 1)}
          disabled={!hasNext}
        >
          Next
        </button>
      </div>
    </div>
  );
}

function buildPageList(current, total) {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages = new Set([1, total, current, current - 1, current + 1]);
  const sorted = [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);

  const result = [];
  let prev = 0;
  for (const value of sorted) {
    if (prev && value - prev > 1) result.push("…");
    result.push(value);
    prev = value;
  }
  return result;
}
