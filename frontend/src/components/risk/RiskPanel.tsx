import { ExposureWidget } from "./ExposureWidget";
import { VaRWidget } from "./VaRWidget";

export function RiskPanel() {
  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">Risk</h2>

      <div className="space-y-3">
        <ExposureWidget label="Notional" value="$4,725.00" max={10000} warn={7000} />
        <ExposureWidget label="Leverage" value="1.5x" max={3} warn={2.5} />
        <ExposureWidget label="Free Margin" value="$5,275.00" />
        <ExposureWidget label="Daily Limit" value="42%" max={100} warn={70} />
      </div>

      <div className="pt-3 border-t border-border">
        <span className="text-xs text-gray-500 uppercase mb-2 block">Value at Risk</span>
        <VaRWidget var95={0.018} var99={0.032} cvar95={0.024} />
      </div>

      <div className="pt-3 border-t border-border">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500 uppercase">MDD Rolling</span>
          <span className="text-loss font-mono">-6.4%</span>
        </div>
      </div>
    </div>
  );
}
