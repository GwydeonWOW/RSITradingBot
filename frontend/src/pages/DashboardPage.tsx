import { MarketPanel } from "@/components/market/MarketPanel";
import { RiskPanel } from "@/components/risk/RiskPanel";
import { ExecutionPanel } from "@/components/execution/ExecutionPanel";
import { OrderBook } from "@/components/execution/OrderBook";
import { FillTable } from "@/components/execution/FillTable";
import { useActiveOrders } from "@/hooks/useMarketData";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWallets, getWalletBalance } from "@/api/wallets";
import { getBotStatus, startBot, stopBot, getBotLogs } from "@/api/signals";

export function DashboardPage() {
  const qc = useQueryClient();
  const { data: ordersData } = useActiveOrders();
  const { data: wallets } = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const { data: bot } = useQuery({ queryKey: ["botStatus"], queryFn: getBotStatus, refetchInterval: 5000, placeholderData: (prev) => prev });
  const { data: logs } = useQuery({ queryKey: ["botLogs"], queryFn: getBotLogs, refetchInterval: 5000, enabled: bot?.running, placeholderData: (prev) => prev });

  const activeWallet = wallets?.[0];
  const { data: balance } = useQuery({
    queryKey: ["walletBalance", activeWallet?.id],
    queryFn: () => getWalletBalance(activeWallet!.id),
    enabled: !!activeWallet?.master_address,
    refetchInterval: 30000,
  });

  const startMut = useMutation({
    mutationFn: startBot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["botStatus"] }),
  });
  const stopMut = useMutation({
    mutationFn: stopBot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["botStatus"] }),
  });

  const orders = ordersData?.orders ?? [];
  const hasWallet = (wallets?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* Top row: Market + Risk + Execution + Account */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="xl:col-span-1"><MarketPanel /></div>
        <div className="xl:col-span-1"><RiskPanel /></div>
        <div className="xl:col-span-1"><ExecutionPanel /></div>

        <div className="bg-surface rounded-xl border border-border p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-300">Account</h2>
          {hasWallet && balance ? (
            <div className="space-y-3">
              <div className="bg-gray-800/50 rounded-lg p-3">
                <span className="text-xs text-gray-500 uppercase">Account Value</span>
                <span className="block text-lg font-semibold text-white font-mono">
                  ${balance.portfolio_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
                {balance.is_unified && <span className="text-[10px] text-profit">Unified Account</span>}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">Perp Margin</span>
                  <span className="block text-white font-mono">${balance.account_value.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-gray-500">Spot USDC</span>
                  <span className="block text-white font-mono">${balance.spot_usdc.toFixed(2)}</span>
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
              </div>
            </div>
          ) : hasWallet ? (
            <div className="space-y-3">
              <ComplianceRow label="Wallet" ok={!!activeWallet?.master_address} detail={activeWallet?.master_address ? "Connected" : "Add account address"} />
            </div>
          ) : (
            <div className="space-y-3">
              <ComplianceRow label="Wallet" ok={false} detail="Not connected" />
            </div>
          )}
        </div>
      </div>

      {/* Bot Control + Log */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-1 bg-surface rounded-xl border border-border p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-300">Bot Control</h2>
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${bot?.running ? "bg-profit animate-pulse" : "bg-gray-600"}`} />
            <span className="text-xs text-gray-400">{bot?.running ? "Running" : "Stopped"}</span>
          </div>
          {bot?.running ? (
            <button
              onClick={() => stopMut.mutate()}
              disabled={stopMut.isPending}
              className="w-full py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
            >
              {stopMut.isPending ? "Stopping..." : "Stop Bot"}
            </button>
          ) : (
            <button
              onClick={() => startMut.mutate()}
              disabled={startMut.isPending || !hasWallet}
              className="w-full py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
            >
              {startMut.isPending ? "Starting..." : "Start Bot"}
            </button>
          )}
          {bot?.last_eval_at && (
            <div className="text-[10px] text-gray-500">
              Last eval: {new Date(bot.last_eval_at).toLocaleTimeString()}
            </div>
          )}
          {bot?.last_error && (
            <div className="text-[10px] text-loss bg-red-900/20 rounded p-1.5">{bot.last_error}</div>
          )}
        </div>

        <div className="xl:col-span-2 bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Bot Log</h2>
          <div className="max-h-80 overflow-y-auto space-y-1 font-mono text-[11px]">
            {logs && logs.logs.length > 0 ? logs.logs.map((l) => (
              <div key={l.id} className={`flex gap-2 py-1 px-2 rounded ${LOG_COLORS[l.level] ?? "text-gray-400"}`}>
                <span className="text-gray-600 shrink-0">{new Date(l.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
                <span className="uppercase text-[9px] font-bold w-14 shrink-0">{l.level}</span>
                <span>{l.message}</span>
              </div>
            )) : (
              <div className="text-center py-8 text-gray-600 text-xs">No log entries yet. Start the bot to see decisions.</div>
            )}
          </div>
        </div>
      </div>

      {/* Order Book + Recent Orders */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Recent Orders</h2>
          {orders.length === 0 ? (
            <div className="text-center py-6 text-gray-600 text-xs">No orders yet. Orders will appear when the bot is actively trading.</div>
          ) : (
            <FillTable orders={orders} />
          )}
        </div>
        <div className="xl:col-span-1"><OrderBook symbol="BTC" /></div>
      </div>
    </div>
  );
}

const LOG_COLORS: Record<string, string> = {
  info: "text-gray-400",
  signal: "text-yellow-400 bg-yellow-900/10",
  trade: "text-profit bg-green-900/10",
  exit: "text-blue-400 bg-blue-900/10",
  error: "text-loss bg-red-900/10",
};

function ComplianceRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${ok ? "bg-profit" : "bg-loss"}`} />
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <span className="text-xs text-gray-500">{detail}</span>
    </div>
  );
}
