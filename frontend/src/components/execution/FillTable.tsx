import type { OrderListItem, OrderStatus } from "@/types";
import clsx from "clsx";

const STATUS_STYLES: Record<OrderStatus, string> = {
  intent: "bg-gray-700 text-gray-300",
  accepted: "bg-blue-900/50 text-blue-400",
  resting: "bg-yellow-900/50 text-yellow-400",
  filling: "bg-purple-900/50 text-purple-400",
  filled: "bg-green-900/50 text-profit",
  canceled: "bg-gray-800 text-gray-500",
  rejected: "bg-red-900/50 text-loss",
  expired: "bg-gray-800 text-gray-500",
};

interface Props {
  orders: OrderListItem[];
}

export function FillTable({ orders }: Props) {
  if (orders.length === 0) {
    return (
      <div className="text-center py-8 text-gray-600 text-sm">
        No recent fills
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 uppercase border-b border-border">
            <th className="text-left py-2 pr-4">Symbol</th>
            <th className="text-left py-2 pr-4">Side</th>
            <th className="text-left py-2 pr-4">Status</th>
            <th className="text-right py-2 pr-4">Size</th>
            <th className="text-right py-2">Filled</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.order_id} className="border-b border-border/50 hover:bg-gray-800/30">
              <td className="py-2 pr-4 font-mono text-white">{order.symbol}</td>
              <td className="py-2 pr-4">
                <span className={order.side === "buy" ? "text-profit" : "text-loss"}>
                  {order.side.toUpperCase()}
                </span>
              </td>
              <td className="py-2 pr-4">
                <span className={clsx("px-1.5 py-0.5 rounded text-[10px] font-medium", STATUS_STYLES[order.status])}>
                  {order.status}
                </span>
              </td>
              <td className="py-2 pr-4 text-right font-mono text-gray-300">
                {order.size.toFixed(4)}
              </td>
              <td className="py-2 text-right font-mono text-gray-300">
                {order.filled_size.toFixed(4)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
