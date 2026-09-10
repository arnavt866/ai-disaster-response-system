import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AXIS_TICK, CHART_TOOLTIP } from "./chartTheme"

function formatTick(iso) {
  if (!iso) return ""
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
}

export default function CoverageTrendChart({ data = [] }) {
  const chartData = data.length
    ? data.map((row, index) => ({
        ...row,
        label: formatTick(row.created_at) || `Run ${index + 1}`,
        coveragePct: Math.round((row.coverage_ratio || 0) * 1000) / 10,
        unmetPct: Math.round((row.unmet_ratio ?? (row.demanded ? row.unmet / row.demanded : 0)) * 1000) / 10,
      }))
    : [{ label: "No runs", allocated: 0, coveragePct: 0, unmetPct: 0 }]

  return (
    <div className="h-64 w-full text-[var(--text-secondary)]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
          <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
          <YAxis
            yAxisId="units"
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
            width={48}
          />
          <YAxis
            yAxisId="pct"
            orientation="right"
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
            width={40}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip
            contentStyle={CHART_TOOLTIP}
            formatter={(value, name) => {
              if (name === "Coverage" || name === "Unmet share") return [`${value}%`, name]
              return [Number(value).toLocaleString(), name]
            }}
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
          <Area
            yAxisId="units"
            type="monotone"
            dataKey="allocated"
            name="Allocated"
            stroke="var(--accent)"
            fill="var(--accent)"
            fillOpacity={0.18}
            strokeWidth={2}
          />
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="coveragePct"
            name="Coverage"
            stroke="var(--severity-ok)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--severity-ok)" }}
          />
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="unmetPct"
            name="Unmet share"
            stroke="var(--severity-critical)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--severity-critical)" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
