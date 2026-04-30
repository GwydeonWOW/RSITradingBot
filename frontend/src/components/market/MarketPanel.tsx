import { useQuery } from "@tanstack/react-query";
import { getMarketData, type MarketTicker } from "@/api/market";

export function MarketPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["market"],
    queryFn: getMarketData,
    refetchInterval: 5000,
  });

  const btc = data?.tickers.find((t) => t.symbol === "BTC");
  const eth = data?.tickers.find((t) => t.symbol === "ETH");

  if (isLoading) {
    return (
      <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
        <h2 className="text-sm font-semibold text-gray-300">Market</h2>
        <div className="text-center py-6 text-gray-600 text-xs">Loading market data...</div>
      </div>
    );
  }

  if (!data || data.count === 0) {
    return (
      <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
        <h2 className="text-sm font-semibold text-gray-300">Market</h2>
        <div className="text-center py-6 text-gray-600 text-xs">
          Unable to fetch market data from Hyperliquid.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">Market</h2>
      <div className="space-y-3">
        {btc && <TickerRow ticker={btc} />}
        {eth && <TickerRow ticker={eth} />}
      </div>
    </div>
  );
}

function TickerRow({ ticker }: { ticker: MarketTicker }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-white">{ticker.symbol}</span>
      </div>
      <div className="mt-1">
        <span className="text-lg font-semibold text-white font-mono">
          ${ticker.mid_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>
    </div>
  );
}
