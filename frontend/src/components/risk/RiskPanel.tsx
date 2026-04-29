export function RiskPanel() {
  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">Risk</h2>
      <div className="text-center py-6 text-gray-600 text-xs">
        No risk data. Connect a wallet and start trading to see risk metrics.
      </div>
    </div>
  );
}
