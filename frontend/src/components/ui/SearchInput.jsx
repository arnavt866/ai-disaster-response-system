import { Search } from "lucide-react";

export default function SearchInput({ value, onChange, placeholder, className = "" }) {
  return (
    <div className={`relative ${className}`}>
      <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
      <input
        type="search"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="ops-input w-full pl-9"
      />
    </div>
  );
}
