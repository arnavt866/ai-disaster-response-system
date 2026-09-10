import { Info } from "lucide-react"

export default function InfoTooltip({ text, label = "More information" }) {
  return (
    <span className="info-tooltip">
      <button
        type="button"
        className="info-tooltip__trigger"
        aria-label={label}
      >
        <Info className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
      <span className="info-tooltip__content" role="tooltip">
        {text}
      </span>
    </span>
  )
}
