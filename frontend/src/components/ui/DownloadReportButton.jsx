import { useState } from "react"
import { Download } from "lucide-react"
import { downloadSituationReportHtml } from "../../api/analytics"

// One treatment everywhere (Dashboard summary, Disasters table, preview page) so
// the action does not read as a primary button in one place and a text link in
// another. Exported so sibling row actions stay in step instead of drifting.
export const REPORT_ACTION_CLASS =
  "ops-btn inline-flex items-center gap-1.5 border border-[var(--border)] bg-[var(--surface)] text-[var(--primary)] hover:bg-[var(--surface-hover)]"

export default function DownloadReportButton({ disasterId, className = "", label = "Download Report" }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  if (!disasterId) return null

  async function handleClick(event) {
    event.preventDefault()
    event.stopPropagation()
    setBusy(true)
    setError("")
    try {
      await downloadSituationReportHtml(disasterId)
    } catch (err) {
      setError(err.message || "Download failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        className={className || REPORT_ACTION_CLASS}
        disabled={busy}
        onClick={handleClick}
        title={label}
      >
        <Download className="h-4 w-4 shrink-0" aria-hidden />
        {busy ? "Preparing…" : label}
      </button>
      {error && <span className="ops-muted">{error}</span>}
    </span>
  )
}
