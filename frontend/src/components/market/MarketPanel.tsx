import { useQuery } from "@tanstack/react-query";
import { getMarketData, type MarketTicker } from "@/api/market";
import { PriceWidget } from "./PriceWidget";

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
  const change = ticker.prev_day_px > 0
    ? ((ticker.mid_price - ticker.prev_day_px) / ticker.prev_day_px) * 100
    : 0;
  const isUp = change >= 0;

  return (
    <div className="bg-gray-800/50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-white">{ticker.symbol}</span>
        <span className={`text-[10px] font-mono ${isUp ? "text-profit" : "text-loss"}`}>
          {isUp ? "+" : ""}{change.toFixed(2)}%
        </span>
      </div>
      <div className="flex items-end justify-between">
        <PriceWidget
          label=""
          value={`$${ticker.mid_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        />
        <div className="text-right">
          <div className="text-[10px] text-gray-500">Funding</div>
          <div className="text-[10px] text-gray-400 font-mono">{(ticker.funding * 100).toFixed(4)}%</div>
        </div>
      </div>
    </div>
  );
}
