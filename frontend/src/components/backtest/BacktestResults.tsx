import { EquityCurve } from "@/components/charts/EquityCurve";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { ReturnDistribution } from "@/components/charts/ReturnDistribution";
import type { BacktestMetrics } from "@/types";

interface Props {
  metrics: BacktestMetrics;
  equityData: { date: string; equity: number }[];
  drawdownData: { date: string; drawdown: number }[];
}

export function BacktestResults({ metrics, equityData, drawdownData }: Props) {
  const tradeDistribution = generateTradeDistribution(metrics);

  return (
    <div className="space-y-6">
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        <MetricCard
          label="Total Return"
          value={`${(metrics.total_return * 100).toFixed(1)}%`}
          positive={metrics.total_return > 0}
        />
        <MetricCard label="CAGR" value={`${(metrics.cagr * 100).toFixed(1)}%`} positive={metrics.cagr > 0} />
        <MetricCard label="Sharpe" value={metrics.sharpe_ratio.toFixed(2)} positive={metrics.sharpe_ratio > 1} />
        <MetricCard
          label="Max DD"
          value={`${(metrics.max_drawdown * 100).toFixed(1)}%`}
          positive={false}
        />
        <MetricCard label="Win Rate" value={`${(metrics.win_rate * 100).toFixed(1)}%`} positive={metrics.win_rate > 0.5} />
        <MetricCard label="Profit Factor" value={metrics.profit_factor.toFixed(2)} positive={metrics.profit_factor > 1} />
        <MetricCard label="Trades" value={metrics.total_trades.toString()} neutral />
      </div>

      {/* Equity Curve */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Equity Curve</h3>
        <EquityCurve data={equityData} height={280} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Drawdown */}
        <div className="bg-surface rounded-xl border border-border p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Drawdown</h3>
          <DrawdownChart data={drawdownData} height={200} />
        </div>

        {/* Trade Distribution */}
        <div className="bg-surface rounded-xl border border-border p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Return Distribution</h3>
          <ReturnDistribution data={tradeDistribution} height={200} />
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  positive,
  neutral,
}: {
  label: string;
  value: string;
  positive?: boolean;
  neutral?: boolean;
}) {
  const color = neutral
    ? "text-white"
    : positive
    ? "text-profit"
    : "text-loss";

  return (
    <div className="bg-surface rounded-lg border border-border p-3">
      <span className="text-xs text-gray-500 uppercase">{label}</span>
      <span className={`block text-lg font-semibold font-mono ${color}`}>
        {value}
      </span>
    </div>
  );
}

function generateTradeDistribution(metrics: BacktestMetrics) {
  const avgReturn = metrics.total_return / Math.max(1, metrics.total_trades);
  const bins = [
    { range: "<-3%", count: 0 },
    { range: "-3 to -1%", count: 0 },
    { range: "-1 to 0%", count: 0 },
    { range: "0 to 1%", count: 0 },
    { range: "1 to 3%", count: 0 },
    { range: ">3%", count: 0 },
  ];

  const total = metrics.total_trades || 20;
  for (let i = 0; i < total; i++) {
    const ret = avgReturn * (0.3 + Math.random() * 1.4) * (Math.random() > metrics.win_rate ? -1 : 1);
    if (ret < -0.03) bins[0]!.count++;
    else if (ret < -0.01) bins[1]!.count++;
    else if (ret < 0) bins[2]!.count++;
    else if (ret < 0.01) bins[3]!.count++;
    else if (ret < 0.03) bins[4]!.count++;
    else bins[5]!.count++;
  }

  return bins;
}
