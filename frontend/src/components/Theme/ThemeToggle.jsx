import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"

function ThemeToggle() {
  const [darkMode, setDarkMode] = useState(() => {
    // Dark is the default; only an explicit "light" preference opts out.
    return localStorage.getItem("theme") !== "light"
  })

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle("dark", darkMode)
    localStorage.setItem("theme", darkMode ? "dark" : "light")
  }, [darkMode])

  return (
    <button
      type="button"
      onClick={() => setDarkMode((prev) => !prev)}
      title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
      className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface-elevated)] px-2.5 py-1.5 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--focus-ring)]"
    >
      {darkMode ? (
        <>
          <Sun className="h-4 w-4" />
          <span>Light</span>
        </>
      ) : (
        <>
          <Moon className="h-4 w-4" />
          <span>Dark</span>
        </>
      )}
    </button>
  )
}

export default ThemeToggle
