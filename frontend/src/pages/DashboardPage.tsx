import { MarketPanel } from "@/components/market/MarketPanel";
import { RiskPanel } from "@/components/risk/RiskPanel";
import { ExecutionPanel } from "@/components/execution/ExecutionPanel";
import { OrderBook } from "@/components/execution/OrderBook";
import { FillTable } from "@/components/execution/FillTable";
import { useActiveOrders } from "@/hooks/useMarketData";
import { useQuery } from "@tanstack/react-query";
import { getWallets } from "@/api/wallets";

export function DashboardPage() {
  const { data: ordersData } = useActiveOrders();
  const { data: wallets } = useQuery({
    queryKey: ["wallets"],
    queryFn: getWallets,
  });

  const orders = ordersData?.orders ?? [];
  const hasWallet = (wallets?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* Top row: Market + Risk + Execution */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="xl:col-span-1">
          <MarketPanel />
        </div>
        <div className="xl:col-span-1">
          <RiskPanel />
        </div>
        <div className="xl:col-span-1">
          <ExecutionPanel />
        </div>

        {/* Compliance Panel */}
        <div className="bg-surface rounded-xl border border-border p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-300">Compliance</h2>
          <div className="space-y-3">
            <ComplianceRow
              label="Agent Wallet"
              ok={hasWallet}
              detail={hasWallet ? "Connected" : "Not connected"}
            />
            <ComplianceRow
              label="API Key"
              ok={false}
              detail="Not configured"
            />
            <ComplianceRow
              label="IP Allowlist"
              ok={false}
              detail="Not configured"
            />
            <ComplianceRow
              label="Log Retention"
              ok={false}
              detail="Not configured"
            />
          </div>
        </div>
      </div>

      {/* Second row: Equity Curve + Order Book */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Equity Curve</h2>
          <div className="text-center py-12 text-gray-600 text-xs">
            No equity data yet. Curve will appear after trades are executed.
          </div>
        </div>
        <div className="xl:col-span-1">
          <OrderBook symbol="BTC" />
        </div>
      </div>

      {/* Third row: Recent Fills */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Recent Orders</h2>
        {orders.length === 0 ? (
          <div className="text-center py-6 text-gray-600 text-xs">
            No orders yet. Orders will appear when the bot is actively trading.
          </div>
        ) : (
          <FillTable orders={orders} />
        )}
      </div>
    </div>
  );
}

function ComplianceRow({
  label,
  ok,
  detail,
}: {
  label: string;
  ok: boolean;
  detail: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${ok ? "bg-profit" : "bg-loss"}`}
        />
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <span className="text-xs text-gray-500">{detail}</span>
    </div>
  );
}
