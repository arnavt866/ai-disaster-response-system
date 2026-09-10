import { Search } from "lucide-react";

export default function SearchInput({ value, onChange, placeholder, className = "" }) {
  return (
    <div className={`ops-input flex items-center gap-2.5 ${className}`}>
      <Search className="h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="min-w-0 flex-1 border-0 bg-transparent p-0 text-[inherit] outline-none focus:ring-0"
      />
    </div>
  );
}
