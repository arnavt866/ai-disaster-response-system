import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AXIS_TICK, CHART_TOOLTIP, priorityFill } from "./chartTheme"

export default function CriticalZonesChart({ data = [] }) {
  const chartData = data.length
    ? data.map((row) => ({
        ...row,
        name: row.zone_name,
      }))
    : [{ name: "No gaps", unmet: 0, priority: "Unknown" }]

  return (
    <div className="h-72 w-full text-[var(--text-secondary)]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 8, right: 16, left: 8, bottom: 4 }}
        >
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} horizontal={false} />
          <XAxis type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="name"
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
            width={160}
          />
          <Tooltip
            contentStyle={CHART_TOOLTIP}
            cursor={{ fill: "var(--tint-neutral)" }}
            formatter={(value, name, item) => [
              `${Number(value).toLocaleString()} unmet`,
              item.payload.priority || name,
            ]}
          />
          <Bar dataKey="unmet" name="Unmet demand" radius={[0, 3, 3, 0]} barSize={16}>
            {chartData.map((entry) => (
              <Cell key={entry.zone_id || entry.name} fill={priorityFill(entry.priority)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
