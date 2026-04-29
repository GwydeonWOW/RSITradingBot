import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listOrders, reconcileOrders } from "@/api/orders";
import { FillTable } from "@/components/execution/FillTable";
import clsx from "clsx";

const STATUS_FLOW: string[] = [
  "intent",
  "accepted",
  "resting",
  "filling",
  "filled",
  "canceled",
  "rejected",
  "expired",
];

export function OrdersPage() {
  const queryClient = useQueryClient();
  const [symbolFilter, setSymbolFilter] = useState<string>("");

  const { data: ordersData, isLoading } = useQuery({
    queryKey: ["orders", symbolFilter],
    queryFn: () => listOrders(symbolFilter || undefined),
    refetchInterval: 5000,
  });

  const reconcileMutation = useMutation({
    mutationFn: reconcileOrders,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const orders = ordersData?.orders ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-white">Orders</h1>
        <div className="flex items-center gap-3">
          <select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-neutral-accent"
          >
            <option value="">All Symbols</option>
            <option value="BTC">BTC</option>
            <option value="ETH">ETH</option>
            <option value="SOL">SOL</option>
          </select>
          <button
            onClick={() => reconcileMutation.mutate()}
            disabled={reconcileMutation.isPending}
            className="px-3 py-1.5 bg-gray-800 text-gray-300 text-xs font-medium rounded-lg hover:bg-gray-700 disabled:opacity-50 border border-gray-700"
          >
            {reconcileMutation.isPending ? "Reconciling..." : "Reconcile"}
          </button>
        </div>
      </div>

      {/* Reconciliation Result */}
      {reconcileMutation.data && (
        <div
          className={`rounded-lg p-3 text-sm ${
            reconcileMutation.data.is_clean
              ? "bg-green-900/20 border border-profit/30 text-profit"
              : "bg-red-900/20 border border-loss/30 text-loss"
          }`}
        >
          {reconcileMutation.data.is_clean
            ? "Reconciliation clean. No discrepancies found."
            : `Found ${reconcileMutation.data.order_discrepancies} order discrepancies and ${reconcileMutation.data.position_discrepancies} position discrepancies.`}
        </div>
      )}

      {/* Order Status Pipeline */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Order Lifecycle</h2>
        <div className="flex items-center gap-1 overflow-x-auto">
          {STATUS_FLOW.map((status, i) => (
            <div key={status} className="flex items-center">
              <div
                className={clsx(
                  "px-2 py-1 rounded text-[10px] font-medium whitespace-nowrap",
                  i < 4 ? "bg-gray-800 text-gray-400" : "bg-gray-900 text-gray-600"
                )}
              >
                {status}
              </div>
              {i < STATUS_FLOW.length - 1 && (
                <svg className="w-3 h-3 text-gray-700 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300">
            Bot Orders ({orders.length})
          </h2>
        </div>
        {isLoading ? (
          <div className="text-center py-8 text-gray-600 text-sm">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="text-center py-8 text-gray-600 text-xs">
            No orders yet. Orders are created automatically when the bot is active.
          </div>
        ) : (
          <FillTable orders={orders} />
        )}
      </div>
    </div>
  );
}
