import { MarketPanel } from "@/components/market/MarketPanel";
import { RiskPanel } from "@/components/risk/RiskPanel";
import { ExecutionPanel } from "@/components/execution/ExecutionPanel";
import { OrderBook } from "@/components/execution/OrderBook";
import { FillTable } from "@/components/execution/FillTable";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { useActiveOrders } from "@/hooks/useMarketData";
import { useMarketStore } from "@/store/useMarketStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useCallback } from "react";
import type { MarketData } from "@/types";

const SAMPLE_EQUITY = Array.from({ length: 60 }, (_, i) => ({
  date: new Date(Date.now() - (60 - i) * 3600000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  }),
  equity: 10000 + Math.sin(i / 5) * 300 + i * 8,
}));

export function DashboardPage() {
  const updateMarket = useMarketStore((s) => s.updateMarket);
  const { data: ordersData } = useActiveOrders();

  const handleMessage = useCallback(
    (data: unknown) => {
      if (data && typeof data === "object" && "symbol" in data) {
        updateMarket(data as MarketData);
      }
    },
    [updateMarket]
  );

  useWebSocket({
    url: "ws://localhost:8000/ws/market",
    onMessage: handleMessage,
    enabled: false,
  });

  const orders = ordersData?.orders ?? [];

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
            <ComplianceRow label="Agent Wallet" ok={true} detail="Connected" />
            <ComplianceRow label="API Key" ok={true} detail="Active" />
            <ComplianceRow label="IP Allowlist" ok={true} detail="192.168.1.0/24" />
            <ComplianceRow label="Log Retention" ok={true} detail="90 days" />
          </div>
        </div>
      </div>

      {/* Second row: Equity Curve + Order Book */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Equity Curve</h2>
          <EquityCurve data={SAMPLE_EQUITY} height={250} />
        </div>
        <div className="xl:col-span-1">
          <OrderBook symbol="BTC" />
        </div>
      </div>

      {/* Third row: Recent Fills */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Recent Orders</h2>
        <FillTable orders={orders} />
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
