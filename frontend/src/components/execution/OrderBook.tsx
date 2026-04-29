interface Props {
  symbol: string;
}

export function OrderBook({ symbol }: Props) {
  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-3">
      <h2 className="text-sm font-semibold text-gray-300">
        Order Book <span className="text-gray-600 ml-1">{symbol}</span>
      </h2>
      <div className="text-center py-6 text-gray-600 text-xs">
        No order book data. Data will appear when connected to the market feed.
      </div>
    </div>
  );
}
