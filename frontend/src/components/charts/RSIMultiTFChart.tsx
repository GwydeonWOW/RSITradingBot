import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";

interface RSIPoint {
  time: string;
  rsi_4h: number;
  rsi_1h: number;
  rsi_15m: number;
}

interface Props {
  data: RSIPoint[];
  height?: number;
}

export function RSIMultiTFChart({ data, height = 250 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="time"
          tick={{ fontSize: 10, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#1f2937" }}
        />
        <YAxis
          domain={[0, 100]}
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
        <ReferenceLine y={55} stroke="#22c55e" strokeDasharray="4 4" strokeOpacity={0.4} />
        <ReferenceLine y={45} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.4} />
        <ReferenceLine y={50} stroke="#6b7280" strokeDasharray="2 2" strokeOpacity={0.3} />
        <Line type="monotone" dataKey="rsi_4h" stroke="#3b82f6" strokeWidth={2} dot={false} name="4H RSI" />
        <Line type="monotone" dataKey="rsi_1h" stroke="#a855f7" strokeWidth={2} dot={false} name="1H RSI" />
        <Line type="monotone" dataKey="rsi_15m" stroke="#6b7280" strokeWidth={1} dot={false} name="15m RSI" />
      </LineChart>
    </ResponsiveContainer>
  );
}
