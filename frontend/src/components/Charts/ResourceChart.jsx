import { useEffect, useRef, useState } from "react";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const SEVERITY_FILL = {
  critical: "var(--severity-critical)",
  high: "var(--severity-high)",
  moderate: "var(--severity-moderate)",
  ok: "var(--severity-ok)",
};

function ResourceChart({ data = [] }) {
  const containerRef = useRef(null);
  const [height, setHeight] = useState(0);
  const chartData = data.length ? data : [{ name: "No data", units: 0 }];

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return undefined;

    const updateHeight = () => {
      const next = Math.round(node.getBoundingClientRect().height);
      if (next > 0) setHeight(next);
    };

    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="h-full min-h-[11rem] w-full text-[var(--text-secondary)]">
      {height > 0 && (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: "currentColor" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "currentColor" }}
              axisLine={false}
              tickLine={false}
              width={44}
            />
            <Tooltip
              cursor={{ fill: "var(--tint-neutral)" }}
              formatter={(value) => [`${Number(value).toLocaleString()} units`, "Available"]}
              contentStyle={{
                backgroundColor: "var(--surface-elevated)",
                color: "var(--text-primary)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                fontSize: "12px",
              }}
            />
            <Bar dataKey="units" radius={[3, 3, 0, 0]} barSize={32} isAnimationActive={false}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={SEVERITY_FILL[entry.severity] || "var(--text-secondary)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default ResourceChart;
