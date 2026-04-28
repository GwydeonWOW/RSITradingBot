import clsx from "clsx";

interface Props {
  label: string;
  value: number;
}

export function RSIWidget({ label, value }: Props) {
  const color =
    value > 55 ? "text-profit" : value < 45 ? "text-loss" : "text-neutral-accent";

  const pct = Math.min(100, Math.max(0, value));

  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-xs text-gray-500 uppercase">{label}</span>
      <div className="relative w-14 h-14">
        <svg className="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
          <circle
            cx="28" cy="28" r="22"
            fill="none" stroke="#1f2937" strokeWidth="4"
          />
          <circle
            cx="28" cy="28" r="22"
            fill="none"
            stroke={value > 55 ? "#22c55e" : value < 45 ? "#ef4444" : "#3b82f6"}
            strokeWidth="4"
            strokeDasharray={`${(pct / 100) * 138.23} 138.23`}
            strokeLinecap="round"
          />
        </svg>
        <span className={clsx("absolute inset-0 flex items-center justify-center text-xs font-bold", color)}>
          {value.toFixed(1)}
        </span>
      </div>
    </div>
  );
}
