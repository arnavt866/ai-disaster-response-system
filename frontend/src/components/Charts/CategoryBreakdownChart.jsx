import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AXIS_TICK, CHART_TOOLTIP } from "./chartTheme"

function compact(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return "0"
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}k`
  return String(Math.round(num))
}

function MiniCategoryChart({ name, allocated, unmet }) {
  const chartData = [
    { key: "Allocated", value: Number(allocated) || 0, fill: "var(--accent)" },
    { key: "Unmet", value: Number(unmet) || 0, fill: "var(--severity-critical)" },
  ]
  const maxVal = Math.max(Number(allocated) || 0, Number(unmet) || 0, 1)

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface-elevated)] px-2 pb-1 pt-2">
      <p className="text-center font-semibold text-[var(--text-primary)]">{name}</p>
      <p className="mb-1 text-center tabular-nums ops-muted">
        Alloc {compact(allocated)} · Unmet {compact(unmet)}
      </p>
      <div className="h-28 w-full text-[var(--text-secondary)]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 14, right: 4, left: 4, bottom: 0 }}>
            <XAxis dataKey="key" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis hide domain={[0, maxVal]} />
            <Tooltip
              contentStyle={CHART_TOOLTIP}
              formatter={(value) => [Number(value).toLocaleString(), ""]}
            />
            <Bar dataKey="value" radius={[3, 3, 0, 0]} barSize={28}>
              {chartData.map((entry) => (
                <Cell key={entry.key} fill={entry.fill} />
              ))}
              <LabelList
                dataKey="value"
                position="top"
                fill="var(--text-primary)"
                fontSize={11}
                formatter={compact}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default function CategoryBreakdownChart({ data = [] }) {
  const chartData = data.length
    ? data.map((row) => ({
        ...row,
        name: String(row.category || "").replace(/^\w/, (ch) => ch.toUpperCase()),
      }))
    : [{ name: "No data", allocated: 0, unmet: 0 }]

  return (
    <div className="grid grid-cols-2 gap-2">
      {chartData.map((row) => (
        <MiniCategoryChart
          key={row.name}
          name={row.name}
          allocated={row.allocated}
          unmet={row.unmet}
        />
      ))}
    </div>
  )
}
