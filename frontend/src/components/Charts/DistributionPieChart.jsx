import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from "recharts"

const COLORS = [
  "var(--primary)",
  "var(--high)",
  "var(--medium)",
  "var(--low)",
  "var(--critical)",
  "var(--success)",
  "#8b5cf6",
  "#06b6d4",
]

export default function DistributionPieChart({ data = [], nameKey = "name", valueKey = "value" }) {
  const chartData = data.length ? data : [{ [nameKey]: "No data", [valueKey]: 1 }]

  return (
    <div className="h-52 w-full text-[var(--text-muted)]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey={valueKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={72}
            paddingAngle={2}
          >
            {chartData.map((entry, index) => (
              <Cell key={entry[nameKey]} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [value, name]}
            contentStyle={{
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              fontSize: "13px",
            }}
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
