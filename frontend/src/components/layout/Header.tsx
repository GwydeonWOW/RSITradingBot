import { useMarketStore } from "@/store/useMarketStore";

export function Header() {
  const markets = useMarketStore((s) => s.markets);
  const btc = markets["BTC"];

  return (
    <header className="sticky top-0 z-30 h-14 bg-gray-900/80 backdrop-blur-sm border-b border-gray-800 flex items-center justify-between px-6">
      <div className="flex items-center gap-6">
        <h1 className="text-sm font-semibold text-gray-300">
          RSI Trading Dashboard
        </h1>
        {btc && (
          <div className="hidden sm:flex items-center gap-4 text-xs">
            <span className="text-gray-500">BTC</span>
            <span className="text-white font-mono">
              ${btc.markPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
            <span
              className={
                btc.regime === "bullish"
                  ? "text-profit"
                  : btc.regime === "bearish"
                  ? "text-loss"
                  : "text-neutral-accent"
              }
            >
              {btc.regime.toUpperCase()}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <div className="w-1.5 h-1.5 rounded-full bg-profit" />
          <span className="hidden md:inline">Connected</span>
        </div>
      </div>
    </header>
  );
}
