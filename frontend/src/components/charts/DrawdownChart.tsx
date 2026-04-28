import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { DrawdownPoint } from "@/types";

interface Props {
  data: DrawdownPoint[];
  height?: number;
}

export function DrawdownChart({ data, height = 200 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#1f2937" }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#1f2937" }}
          tickFormatter={(v: number) => `${v.toFixed(1)}%`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#111827",
            border: "1px solid #1f2937",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          labelStyle={{ color: "#9ca3af" }}
          formatter={(value: number) => [`${value.toFixed(2)}%`, "Drawdown"]}
        />
        <Area
          type="monotone"
          dataKey="drawdown"
          stroke="#ef4444"
          strokeWidth={2}
          fill="url(#ddGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
