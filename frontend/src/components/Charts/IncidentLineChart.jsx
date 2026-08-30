import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

export default function IncidentLineChart({ data = [] }) {
  const chartData = data.length ? data : [{ date: "No data", count: 0 }]

  return (
    <div className="h-52 w-full text-[var(--text-muted)]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: "currentColor" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: "currentColor" }} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip
            formatter={(value) => [`${value} incidents`, "Count"]}
            contentStyle={{
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              fontSize: "13px",
            }}
          />
          <Area type="monotone" dataKey="count" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.15} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
