import { EquityCurve } from "@/components/charts/EquityCurve";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { ReturnDistribution } from "@/components/charts/ReturnDistribution";

const SAMPLE_METRICS = {
  totalReturn: 34.2,
  cagr: 28.5,
  sharpe: 1.67,
  sortino: 2.14,
  maxDrawdown: -12.8,
  winRate: 58.3,
  profitFactor: 1.84,
  expectancy: 0.42,
  avgR: 0.67,
  calmar: 2.23,
  totalTrades: 47,
};

const SAMPLE_EQUITY = Array.from({ length: 90 }, (_, i) => {
  const base = 10000 + i * 40;
  const noise = Math.sin(i / 5) * 200 + Math.random() * 100;
  return {
    date: new Date(2024, 0, 1 + i * 4).toISOString().slice(0, 10),
    equity: Math.round(base + noise),
  };
});

const SAMPLE_DD = (() => {
  let peak = 0;
  return SAMPLE_EQUITY.map((pt) => {
    peak = Math.max(peak, pt.equity);
    const dd = ((pt.equity - peak) / peak) * 100;
    return { date: pt.date, drawdown: Math.round(dd * 100) / 100 };
  });
})();

const RETURN_BINS = [
  { range: "<-3%", count: 2 },
  { range: "-3 to -1%", count: 5 },
  { range: "-1 to 0%", count: 8 },
  { range: "0 to 1%", count: 12 },
  { range: "1 to 3%", count: 14 },
  { range: ">3%", count: 6 },
];

const MONTHLY_DATA = [
  { month: "Jan", return: 4.2, trades: 6 },
  { month: "Feb", return: -1.8, trades: 4 },
  { month: "Mar", return: 6.1, trades: 8 },
  { month: "Apr", return: 2.4, trades: 5 },
  { month: "May", return: -3.2, trades: 3 },
  { month: "Jun", return: 5.8, trades: 7 },
  { month: "Jul", return: 3.1, trades: 5 },
  { month: "Aug", return: -0.5, trades: 4 },
  { month: "Sep", return: 7.2, trades: 9 },
  { month: "Oct", return: 1.9, trades: 3 },
  { month: "Nov", return: 4.8, trades: 6 },
  { month: "Dec", return: 3.2, trades: 5 },
];

export function PerformancePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-white">Performance</h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard label="Total Return" value={`${SAMPLE_METRICS.totalReturn}%`} positive={SAMPLE_METRICS.totalReturn > 0} />
        <MetricCard label="CAGR" value={`${SAMPLE_METRICS.cagr}%`} positive={SAMPLE_METRICS.cagr > 0} />
        <MetricCard label="Sharpe" value={SAMPLE_METRICS.sharpe.toFixed(2)} positive={SAMPLE_METRICS.sharpe > 1} />
        <MetricCard label="Sortino" value={SAMPLE_METRICS.sortino.toFixed(2)} positive={SAMPLE_METRICS.sortino > 1} />
        <MetricCard label="Max DD" value={`${SAMPLE_METRICS.maxDrawdown}%`} positive={false} />
        <MetricCard label="Win Rate" value={`${SAMPLE_METRICS.winRate}%`} positive={SAMPLE_METRICS.winRate > 50} />
        <MetricCard label="Profit Factor" value={SAMPLE_METRICS.profitFactor.toFixed(2)} positive={SAMPLE_METRICS.profitFactor > 1} />
        <MetricCard label="Expectancy" value={`$${SAMPLE_METRICS.expectancy}`} positive={SAMPLE_METRICS.expectancy > 0} />
        <MetricCard label="Avg R-Multiple" value={SAMPLE_METRICS.avgR.toFixed(2)} positive={SAMPLE_METRICS.avgR > 0} />
        <MetricCard label="Calmar" value={SAMPLE_METRICS.calmar.toFixed(2)} positive={SAMPLE_METRICS.calmar > 1} />
        <MetricCard label="Total Trades" value={SAMPLE_METRICS.totalTrades.toString()} neutral />
      </div>

      {/* Equity Curve */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Equity Curve</h2>
        <EquityCurve data={SAMPLE_EQUITY} height={280} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Drawdown */}
        <div className="bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Drawdown</h2>
          <DrawdownChart data={SAMPLE_DD} height={200} />
        </div>

        {/* Return Distribution */}
        <div className="bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Return Distribution</h2>
          <ReturnDistribution data={RETURN_BINS} height={200} />
        </div>
      </div>

      {/* Monthly Breakdown */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Monthly Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 uppercase border-b border-border">
                <th className="text-left py-2 px-3">Month</th>
                <th className="text-right py-2 px-3">Return</th>
                <th className="text-right py-2 px-3">Trades</th>
              </tr>
            </thead>
            <tbody>
              {MONTHLY_DATA.map((row) => (
                <tr key={row.month} className="border-b border-border/50 hover:bg-gray-800/30">
                  <td className="py-2 px-3 text-gray-300 font-medium">{row.month}</td>
                  <td className={`py-2 px-3 text-right font-mono ${row.return >= 0 ? "text-profit" : "text-loss"}`}>
                    {row.return >= 0 ? "+" : ""}{row.return.toFixed(1)}%
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-gray-400">{row.trades}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
  const color = neutral ? "text-white" : positive ? "text-profit" : "text-loss";
  return (
    <div className="bg-surface rounded-lg border border-border p-3">
      <span className="text-xs text-gray-500 uppercase block">{label}</span>
      <span className={`text-lg font-semibold font-mono ${color}`}>{value}</span>
    </div>
  );
}
