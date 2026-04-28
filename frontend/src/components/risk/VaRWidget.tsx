interface Props {
  var95: number;
  var99: number;
  cvar95: number;
}

export function VaRWidget({ var95, var99, cvar95 }: Props) {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="text-center">
        <span className="block text-xs text-gray-500">VaR 95%</span>
        <span className="text-sm font-mono text-yellow-500">
          {(var95 * 100).toFixed(2)}%
        </span>
      </div>
      <div className="text-center">
        <span className="block text-xs text-gray-500">VaR 99%</span>
        <span className="text-sm font-mono text-loss">
          {(var99 * 100).toFixed(2)}%
        </span>
      </div>
      <div className="text-center">
        <span className="block text-xs text-gray-500">CVaR 95%</span>
        <span className="text-sm font-mono text-loss">
          {(cvar95 * 100).toFixed(2)}%
        </span>
      </div>
    </div>
  );
}
