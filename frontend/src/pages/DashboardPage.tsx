import { MarketPanel } from "@/components/market/MarketPanel";
import { RiskPanel } from "@/components/risk/RiskPanel";
import { ExecutionPanel } from "@/components/execution/ExecutionPanel";
import { OrderBook } from "@/components/execution/OrderBook";
import { FillTable } from "@/components/execution/FillTable";
import { useActiveOrders } from "@/hooks/useMarketData";
import { useQuery } from "@tanstack/react-query";
import { getWallets } from "@/api/wallets";
import { getWalletBalance } from "@/api/wallets";

export function DashboardPage() {
  const { data: ordersData } = useActiveOrders();
  const { data: wallets } = useQuery({
    queryKey: ["wallets"],
    queryFn: getWallets,
  });

  const activeWallet = wallets?.[0];
  const { data: balance } = useQuery({
    queryKey: ["walletBalance", activeWallet?.id],
    queryFn: () => getWalletBalance(activeWallet!.id),
    enabled: !!activeWallet?.master_address,
    refetchInterval: 30000,
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

        {/* Wallet & Compliance Panel */}
        <div className="bg-surface rounded-xl border border-border p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-300">Account</h2>
          {hasWallet && balance ? (
            <div className="space-y-3">
              <div className="bg-gray-800/50 rounded-lg p-3">
                <span className="text-xs text-gray-500 uppercase">Account Value</span>
                <span className="block text-lg font-semibold text-white font-mono">
                  ${balance.account_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              {balance.account_value === 0 && (
                <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-2 text-[10px] text-yellow-400 space-y-1">
                  <div>Balance is $0. Queried address: <span className="font-mono">{balance.queried_address}</span></div>
                  <div>Using: {balance.used_master ? "Account address (master)" : "API wallet address (agent)"} — {balance.used_master ? "correct" : "add your Account Address in Settings for accurate balance"}</div>
                  <div>Check Coolify backend logs for "Balance query:" to see the raw address being sent to Hyperliquid.</div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">Withdrawable</span>
                  <span className="block text-white font-mono">${balance.withdrawable.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-gray-500">Margin Used</span>
                  <span className="block text-white font-mono">${balance.margin_used.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-gray-500">Unrealized PnL</span>
                  <span className={`block font-mono ${balance.unrealized_pnl >= 0 ? "text-profit" : "text-loss"}`}>
                    ${balance.unrealized_pnl.toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Raw USD</span>
                  <span className="block text-white font-mono">${balance.total_raw_usd.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ) : hasWallet && !activeWallet?.master_address ? (
            <div className="space-y-3">
              <ComplianceRow label="Wallet" ok={true} detail="Connected" />
              <ComplianceRow label="Balance" ok={false} detail="Add account address" />
            </div>
          ) : (
            <div className="space-y-3">
              <ComplianceRow label="Wallet" ok={false} detail="Not connected" />
            </div>
          )}
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
