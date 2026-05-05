import { MarketPanel } from "@/components/market/MarketPanel";
import { RiskPanel } from "@/components/risk/RiskPanel";
import { ExecutionPanel } from "@/components/execution/ExecutionPanel";
import { OrderBook } from "@/components/execution/OrderBook";
import { FillTable } from "@/components/execution/FillTable";
import { useActiveOrders } from "@/hooks/useMarketData";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWallets, getWalletBalance } from "@/api/wallets";
import { getBotStatus, startBot, stopBot, getBotLogs } from "@/api/signals";
import { getOpenPositions } from "@/api/orders";

export function DashboardPage() {
  const qc = useQueryClient();
  const { data: ordersData } = useActiveOrders();
  const { data: wallets } = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const { data: bot } = useQuery({ queryKey: ["botStatus"], queryFn: getBotStatus, refetchInterval: 5000, placeholderData: (prev) => prev });
  const { data: logs } = useQuery({ queryKey: ["botLogs"], queryFn: getBotLogs, refetchInterval: 5000, enabled: bot?.running, placeholderData: (prev) => prev });
  const { data: positionsData } = useQuery({ queryKey: ["openPositions"], queryFn: getOpenPositions, refetchInterval: 5000, placeholderData: (prev) => prev });

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
    onError: () => qc.invalidateQueries({ queryKey: ["botStatus"] }),
  });
  const stopMut = useMutation({
    mutationFn: stopBot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["botStatus"] }),
    onError: () => qc.invalidateQueries({ queryKey: ["botStatus"] }),
  });

  // Optimistic state: show intended state during mutation
  const isPending = startMut.isPending || stopMut.isPending;
  const displayRunning = startMut.isPending ? true : stopMut.isPending ? false : !!bot?.running;

  const orders = ordersData?.orders ?? [];
  const hasWallet = (wallets?.length ?? 0) > 0;
  const openPositions = positionsData?.positions ?? [];
  const orderBookSymbol = openPositions[0]?.symbol ?? "BTC";

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
            <div className={`w-3 h-3 rounded-full ${displayRunning ? "bg-profit animate-pulse" : "bg-gray-600"}`} />
            <span className="text-xs text-gray-400">
              {isPending ? (startMut.isPending ? "Starting..." : "Stopping...") : (displayRunning ? "Running" : "Stopped")}
            </span>
          </div>
          <button
            onClick={() => displayRunning ? stopMut.mutate() : startMut.mutate()}
            disabled={isPending || (!displayRunning && !hasWallet)}
            className={`w-full py-2 text-white text-xs font-semibold rounded-lg disabled:opacity-50 ${
              displayRunning
                ? "bg-red-600 hover:bg-red-700"
                : "bg-green-600 hover:bg-green-700"
            }`}
          >
            {isPending
              ? (startMut.isPending ? "Starting..." : "Stopping...")
              : (displayRunning ? "Stop Bot" : "Start Bot")}
          </button>
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

      {/* Open Positions */}
      {openPositions.length > 0 && (
        <div className="bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Open Positions</h2>
          <div className="space-y-2">
            {openPositions.map((p) => (
              <div key={p.id} className="grid grid-cols-2 md:grid-cols-6 gap-3 bg-gray-800/40 rounded-lg p-3 text-xs">
                <div>
                  <span className="text-gray-500">Symbol</span>
                  <span className={`block font-semibold ${p.side === "long" ? "text-profit" : "text-loss"}`}>
                    {p.symbol} {p.side.toUpperCase()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Size / Entry</span>
                  <span className="block font-mono text-white">{p.size} @ ${p.entry_price.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-gray-500">Current</span>
                  <span className="block font-mono text-white">{p.current_price ? `$${p.current_price.toFixed(2)}` : "—"}</span>
                </div>
                <div>
                  <span className="text-gray-500">Unrealized PnL</span>
                  <span className={`block font-mono font-semibold ${p.unrealized_pnl >= 0 ? "text-profit" : "text-loss"}`}>
                    ${p.unrealized_pnl.toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Stop Loss</span>
                  <span className="block font-mono text-white">{p.stop_loss ? `$${p.stop_loss.toFixed(2)}` : "—"}</span>
                </div>
                <div>
                  <span className="text-gray-500">Leverage / Held</span>
                  <span className="block font-mono text-white">{p.leverage}x / {p.opened_at ? formatHeld(p.opened_at) : "—"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
        <div className="xl:col-span-1"><OrderBook symbol={orderBookSymbol} /></div>
      </div>
    </div>
  );
}

const LOG_COLORS: Record<string, string> = {
  info: "text-gray-400",
  signal: "text-yellow-400 bg-yellow-900/10",
  trade: "text-profit bg-green-900/10",
  exit: "text-blue-400 bg-blue-900/10",
  tracking: "text-cyan-400 bg-cyan-900/10",
  error: "text-loss bg-red-900/10",
};

function formatHeld(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

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
