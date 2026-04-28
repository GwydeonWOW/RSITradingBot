import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";

interface Props {
  data: { range: string; count: number }[];
  height?: number;
}

export function ReturnDistribution({ data, height = 200 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="range"
          tick={{ fontSize: 9, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#1f2937" }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#1f2937" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#111827",
            border: "1px solid #1f2937",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          labelStyle={{ color: "#9ca3af" }}
        />
        <Bar dataKey="count" radius={[2, 2, 0, 0]}>
          {data.map((entry, index) => {
            const isNeg = entry.range.startsWith("-");
            return (
              <Cell
                key={index}
                fill={isNeg ? "#ef4444" : "#22c55e"}
                fillOpacity={0.7}
              />
            );
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
