import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

function ResourceChart({ data = [] }) {
  const chartData = data.length
    ? data
    : [{ name: "No data", units: 0 }]

  return (
    <div className="h-52 w-full text-[var(--text-muted)]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "currentColor" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "currentColor" }} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value) => [`${Number(value).toLocaleString()} units`, "Available"]}
            contentStyle={{
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          />
          <Bar dataKey="units" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={36} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default ResourceChart
