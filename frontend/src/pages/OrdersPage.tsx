import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listOrders, submitOrder, reconcileOrders } from "@/api/orders";
import { FillTable } from "@/components/execution/FillTable";
import type { OrderSide, OrderType } from "@/types";
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
  const [showForm, setShowForm] = useState(false);

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
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-3 py-1.5 bg-neutral-accent text-white text-xs font-semibold rounded-lg hover:bg-neutral-accent/90"
          >
            {showForm ? "Cancel" : "New Order"}
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

      {/* New Order Form */}
      {showForm && <NewOrderForm onClose={() => setShowForm(false)} />}

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
            Active Orders ({orders.length})
          </h2>
        </div>
        {isLoading ? (
          <div className="text-center py-8 text-gray-600 text-sm">Loading orders...</div>
        ) : (
          <FillTable orders={orders} />
        )}
      </div>
    </div>
  );
}

function NewOrderForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState("BTC");
  const [side, setSide] = useState<OrderSide>("buy");
  const [size, setSize] = useState("0.01");
  const [orderType, setOrderType] = useState<OrderType>("market");
  const [price, setPrice] = useState("");

  const mutation = useMutation({
    mutationFn: submitOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      symbol,
      side,
      size: parseFloat(size),
      order_type: orderType,
      price: price ? parseFloat(price) : undefined,
    });
  }

  const inputClass =
    "w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-neutral-accent focus:border-neutral-accent";

  return (
    <div className="bg-surface rounded-xl border border-border p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Submit Order</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div>
          <label className="block text-xs text-gray-500 uppercase mb-1">Symbol</label>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className={inputClass}>
            <option value="BTC">BTC</option>
            <option value="ETH">ETH</option>
            <option value="SOL">SOL</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 uppercase mb-1">Side</label>
          <select value={side} onChange={(e) => setSide(e.target.value as OrderSide)} className={inputClass}>
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 uppercase mb-1">Size</label>
          <input
            type="number"
            min="0.001"
            step="0.001"
            value={size}
            onChange={(e) => setSize(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 uppercase mb-1">Type</label>
          <select value={orderType} onChange={(e) => setOrderType(e.target.value as OrderType)} className={inputClass}>
            <option value="market">Market</option>
            <option value="limit">Limit</option>
            <option value="stop_market">Stop Market</option>
          </select>
        </div>
        {(orderType === "limit" || orderType === "stop_market") && (
          <div>
            <label className="block text-xs text-gray-500 uppercase mb-1">Price</label>
            <input
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
              className={inputClass}
            />
          </div>
        )}
        <div className="flex items-end">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full px-4 py-2 bg-profit text-gray-950 text-sm font-semibold rounded-lg hover:bg-profit/90 disabled:opacity-50"
          >
            {mutation.isPending ? "Submitting..." : "Submit"}
          </button>
        </div>
      </form>
      {mutation.isError && (
        <p className="text-xs text-loss mt-2">{(mutation.error as Error).message}</p>
      )}
    </div>
  );
}
