import ThemeToggle from "../Theme/ThemeToggle"

function Navbar() {
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-4 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-2 w-2 rounded-full bg-[var(--success)]" aria-hidden />
        <h1 className="text-sm font-semibold text-[var(--text-primary)] sm:text-base">
          Disaster Response Command Center
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <ThemeToggle />
      </div>
    </header>
  )
}

export default Navbar
