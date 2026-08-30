import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"

function ThemeToggle() {
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem("theme") === "dark"
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
      className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] focus:outline-2 focus:outline-offset-1 focus:outline-[var(--primary)]"
    >
      {darkMode ? (
        <>
          <Sun className="h-4 w-4 text-[var(--warning)]" />
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
