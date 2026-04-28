import { useMarketStore } from "@/store/useMarketStore";
import { RegimeIndicator } from "./RegimeIndicator";
import { RSIWidget } from "./RSIWidget";
import { PriceWidget } from "./PriceWidget";

export function MarketPanel() {
  const markets = useMarketStore((s) => s.markets);
  const btc = markets["BTC"]!;

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">Market</h2>
        <RegimeIndicator regime={btc.regime} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <PriceWidget
          label="Mark Price"
          value={`$${btc.markPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          sublabel={`Spread: ${(btc.spread * 100).toFixed(2)}%`}
        />
        <PriceWidget
          label="Book"
          value={`${btc.bidSize.toFixed(1)} / ${btc.askSize.toFixed(1)}`}
          sublabel="Bid / Ask size"
        />
      </div>

      <div className="flex items-center justify-around pt-2 border-t border-border">
        <RSIWidget label="4H" value={btc.rsi_4h} />
        <RSIWidget label="1H" value={btc.rsi_1h} />
        <RSIWidget label="15m" value={btc.rsi_15m} />
      </div>
    </div>
  );
}
