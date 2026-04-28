export function ExecutionPanel() {
  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">Execution</h2>

      <div className="grid grid-cols-2 gap-4">
        <MetricBlock label="Fill Ratio" value="94.2%" color="text-profit" />
        <MetricBlock label="Avg Slippage" value="0.03%" color="text-yellow-500" />
        <MetricBlock label="Funding Rate" value="0.0085%" color="text-neutral-accent" />
        <MetricBlock label="Open Orders" value="3" color="text-white" />
      </div>

      <div className="pt-3 border-t border-border">
        <span className="text-xs text-gray-500 uppercase mb-3 block">Latency (ms)</span>
        <div className="grid grid-cols-3 gap-3">
          <LatencyBlock label="p50" value={12} />
          <LatencyBlock label="p95" value={28} />
          <LatencyBlock label="p99" value={65} />
        </div>
      </div>
    </div>
  );
}

function MetricBlock({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3">
      <span className="text-xs text-gray-500 uppercase">{label}</span>
      <span className={`block text-lg font-semibold font-mono ${color}`}>
        {value}
      </span>
    </div>
  );
}

function LatencyBlock({ label, value }: { label: string; value: number }) {
  const color = value > 50 ? "text-loss" : value > 25 ? "text-yellow-500" : "text-profit";
  return (
    <div className="text-center">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`block text-sm font-mono font-semibold ${color}`}>
        {value}ms
      </span>
    </div>
  );
}
