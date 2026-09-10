import { Brain } from "lucide-react";

/**
 * Compact inline marker that allocation/demand figures are ML- or optimization-driven.
 */
export default function AiEngineLabel({ children, className = "", title }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border border-[var(--accent)]/35 bg-[var(--tint-accent)] px-2 py-0.5 text-xs font-semibold text-[var(--accent-text)] ${className}`}
      title={title}
    >
      <Brain className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}
