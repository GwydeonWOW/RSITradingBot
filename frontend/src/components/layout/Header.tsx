import { useQuery } from "@tanstack/react-query";
import { getMarketData } from "@/api/market";

export function Header() {
  const { data } = useQuery({
    queryKey: ["market"],
    queryFn: getMarketData,
    refetchInterval: 10000,
  });

  const btc = data?.tickers.find((t) => t.symbol === "BTC");
  const change = btc && btc.prev_day_px > 0
    ? ((btc.mid_price - btc.prev_day_px) / btc.prev_day_px) * 100
    : null;

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
              ${btc.mid_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
            {change !== null && (
              <span className={change >= 0 ? "text-profit" : "text-loss"}>
                {change >= 0 ? "+" : ""}{change.toFixed(2)}%
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <div className={`w-1.5 h-1.5 rounded-full ${data && data.count > 0 ? "bg-profit" : "bg-gray-600"}`} />
          <span className="hidden md:inline">{data && data.count > 0 ? "Connected" : "Offline"}</span>
        </div>
      </div>
    </header>
  );
}
