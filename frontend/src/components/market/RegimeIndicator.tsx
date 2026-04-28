import type { Regime } from "@/types";
import clsx from "clsx";

interface Props {
  regime: Regime;
}

export function RegimeIndicator({ regime }: Props) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={clsx(
          "w-3 h-3 rounded-full",
          regime === "bullish" && "bg-profit",
          regime === "bearish" && "bg-loss",
          regime === "neutral" && "bg-neutral-accent"
        )}
      />
      <span
        className={clsx(
          "text-sm font-semibold uppercase tracking-wider",
          regime === "bullish" && "text-profit",
          regime === "bearish" && "text-loss",
          regime === "neutral" && "text-neutral-accent"
        )}
      >
        {regime}
      </span>
    </div>
  );
}
