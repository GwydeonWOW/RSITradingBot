import { useQuery } from "@tanstack/react-query";
import { getPerformanceSummary } from "@/api/reports";

export function PerformancePage() {
  const { data: perf, isLoading } = useQuery({
    queryKey: ["performance"],
    queryFn: getPerformanceSummary,
  });

  const hasData = perf && perf.total_trades && (perf.total_trades as number) > 0;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-white">Performance</h1>

      {isLoading ? (
        <div className="text-center py-12 text-gray-600 text-sm">Loading performance data...</div>
      ) : !hasData ? (
        <div className="bg-surface rounded-xl border border-border p-8 text-center">
          <p className="text-gray-400 text-sm">No performance data yet.</p>
          <p className="text-gray-600 text-xs mt-1">Metrics will appear after trades are closed by the bot.</p>
        </div>
      ) : (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <MetricCard label="Total Trades" value={String(perf.total_trades)} neutral />
            <MetricCard label="Win Rate" value={`${((perf.win_rate as number) * 100).toFixed(1)}%`} positive={(perf.win_rate as number) > 0.5} />
            <MetricCard label="Total PnL" value={`$${(perf.total_pnl as number).toFixed(2)}`} positive={(perf.total_pnl as number) > 0} />
            <MetricCard label="Profit Factor" value={(perf.profit_factor as number).toFixed(2)} positive={(perf.profit_factor as number) > 1} />
            <MetricCard label="Best Trade" value={`$${(perf.best_trade as number).toFixed(2)}`} positive />
            <MetricCard label="Worst Trade" value={`$${(perf.worst_trade as number).toFixed(2)}`} positive={false} />
            <MetricCard label="Avg PnL" value={`$${(perf.avg_pnl as number).toFixed(2)}`} positive={(perf.avg_pnl as number) > 0} />
            <MetricCard label="Winners" value={String(perf.winners)} positive />
            <MetricCard label="Losers" value={String(perf.losers)} positive={false} />
            <MetricCard label="Gross Profit" value={`$${(perf.gross_profit as number).toFixed(2)}`} positive />
            <MetricCard label="Gross Loss" value={`$${(perf.gross_loss as number).toFixed(2)}`} positive={false} />
          </div>
        </>
      )}
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
