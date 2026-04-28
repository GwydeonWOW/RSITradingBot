interface Props {
  windows: WalkforwardWindow[];
}

export interface WalkforwardWindow {
  window: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  sharpe_ratio: number;
  total_return: number;
  max_drawdown: number;
  trades: number;
}

export function WalkforwardResults({ windows }: Props) {
  if (windows.length === 0) {
    return (
      <div className="bg-surface rounded-xl border border-border p-6 text-center text-gray-600 text-sm">
        No walk-forward results yet. Configure parameters and run the validation.
      </div>
    );
  }

  const avgSharpe = windows.reduce((s, w) => s + w.sharpe_ratio, 0) / windows.length;
  const avgReturn = windows.reduce((s, w) => s + w.total_return, 0) / windows.length;
  const avgDD = windows.reduce((s, w) => s + w.max_drawdown, 0) / windows.length;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-surface rounded-lg border border-border p-3 text-center">
          <span className="text-xs text-gray-500 uppercase">Avg Sharpe</span>
          <span className={`block text-lg font-semibold font-mono ${avgSharpe > 1 ? "text-profit" : "text-loss"}`}>
            {avgSharpe.toFixed(2)}
          </span>
        </div>
        <div className="bg-surface rounded-lg border border-border p-3 text-center">
          <span className="text-xs text-gray-500 uppercase">Avg Return</span>
          <span className={`block text-lg font-semibold font-mono ${avgReturn > 0 ? "text-profit" : "text-loss"}`}>
            {(avgReturn * 100).toFixed(1)}%
          </span>
        </div>
        <div className="bg-surface rounded-lg border border-border p-3 text-center">
          <span className="text-xs text-gray-500 uppercase">Avg MDD</span>
          <span className="block text-lg font-semibold font-mono text-loss">
            {(avgDD * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 uppercase border-b border-border">
              <th className="text-left py-2 px-2">Window</th>
              <th className="text-left py-2 px-2">Train Period</th>
              <th className="text-left py-2 px-2">Test Period</th>
              <th className="text-right py-2 px-2">Sharpe</th>
              <th className="text-right py-2 px-2">Return</th>
              <th className="text-right py-2 px-2">MDD</th>
              <th className="text-right py-2 px-2">Trades</th>
            </tr>
          </thead>
          <tbody>
            {windows.map((w) => (
              <tr key={w.window} className="border-b border-border/50 hover:bg-gray-800/30">
                <td className="py-2 px-2 text-white font-mono">{w.window}</td>
                <td className="py-2 px-2 text-gray-400">{w.train_start} - {w.train_end}</td>
                <td className="py-2 px-2 text-gray-400">{w.test_start} - {w.test_end}</td>
                <td className={`py-2 px-2 text-right font-mono ${w.sharpe_ratio > 1 ? "text-profit" : "text-loss"}`}>
                  {w.sharpe_ratio.toFixed(2)}
                </td>
                <td className={`py-2 px-2 text-right font-mono ${w.total_return > 0 ? "text-profit" : "text-loss"}`}>
                  {(w.total_return * 100).toFixed(1)}%
                </td>
                <td className="py-2 px-2 text-right font-mono text-loss">
                  {(w.max_drawdown * 100).toFixed(1)}%
                </td>
                <td className="py-2 px-2 text-right font-mono text-gray-300">{w.trades}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
