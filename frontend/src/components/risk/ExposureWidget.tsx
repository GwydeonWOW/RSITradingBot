interface Props {
  label: string;
  value: string | number;
  max?: number;
  warn?: number;
}

export function ExposureWidget({ label, value, max, warn }: Props) {
  const numVal = typeof value === "number" ? value : parseFloat(value);
  const isWarning = warn !== undefined && numVal >= warn;
  const isDanger = max !== undefined && numVal >= max * 0.9;

  const barPct = max ? Math.min(100, (numVal / max) * 100) : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500 uppercase">{label}</span>
        <span
          className={
            isDanger ? "text-loss font-semibold" : isWarning ? "text-yellow-500 font-semibold" : "text-white"
          }
        >
          {value}
        </span>
      </div>
      {max !== undefined && (
        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isDanger ? "bg-loss" : isWarning ? "bg-yellow-500" : "bg-profit"
            }`}
            style={{ width: `${barPct}%` }}
          />
        </div>
      )}
    </div>
  );
}
