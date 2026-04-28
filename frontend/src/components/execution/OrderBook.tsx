interface Props {
  symbol: string;
}

interface BookRow {
  price: number;
  size: number;
  total: number;
}

export function OrderBook({ symbol }: Props) {
  const bids = generateBookRows(10, 94450, 94550, true);
  const asks = generateBookRows(10, 94550, 94650, false);

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-3">
      <h2 className="text-sm font-semibold text-gray-300">
        Order Book <span className="text-gray-600 ml-1">{symbol}</span>
      </h2>

      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <div className="flex justify-between text-gray-500 mb-1">
            <span>Price</span>
            <span>Size</span>
          </div>
          {bids.map((row, i) => (
            <div key={i} className="flex justify-between py-0.5 relative">
              <div
                className="absolute inset-y-0 right-0 bg-profit/10"
                style={{ width: `${(row.total / bids[0]!.total) * 100}%` }}
              />
              <span className="relative text-profit font-mono">
                {row.price.toFixed(2)}
              </span>
              <span className="relative text-gray-400 font-mono">
                {row.size.toFixed(4)}
              </span>
            </div>
          ))}
        </div>

        <div>
          <div className="flex justify-between text-gray-500 mb-1">
            <span>Price</span>
            <span>Size</span>
          </div>
          {asks.map((row, i) => (
            <div key={i} className="flex justify-between py-0.5 relative">
              <div
                className="absolute inset-y-0 left-0 bg-loss/10"
                style={{ width: `${(row.total / asks[0]!.total) * 100}%` }}
              />
              <span className="relative text-loss font-mono">
                {row.price.toFixed(2)}
              </span>
              <span className="relative text-gray-400 font-mono">
                {row.size.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function generateBookRows(
  count: number,
  low: number,
  high: number,
  isBid: boolean
): BookRow[] {
  const rows: BookRow[] = [];
  let total = 0;
  for (let i = 0; i < count; i++) {
    const price = isBid
      ? high - i * (high - low) / count
      : low + i * (high - low) / count;
    const size = 0.1 + Math.random() * 2;
    total += size;
    rows.push({ price, size, total });
  }
  return rows;
}
