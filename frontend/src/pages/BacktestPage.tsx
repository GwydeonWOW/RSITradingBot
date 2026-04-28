import { useState } from "react";
import { BacktestForm } from "@/components/backtest/BacktestForm";
import { BacktestResults } from "@/components/backtest/BacktestResults";
import { WalkforwardResults } from "@/components/backtest/WalkforwardResults";
import type { BacktestMetrics } from "@/types";

export function BacktestPage() {
  const [result, setResult] = useState<{
    result_id: string;
    total_trades: number;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<"backtest" | "walkforward">("backtest");

  const sampleMetrics: BacktestMetrics = {
    total_return: 0.342,
    cagr: 0.285,
    sharpe_ratio: 1.67,
    max_drawdown: -0.128,
    win_rate: 0.583,
    profit_factor: 1.84,
    total_trades: 47,
  };

  const sampleEquity = generateSampleEquity();
  const sampleDrawdown = generateSampleDrawdown();

  const displayMetrics = result ? sampleMetrics : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-white">Backtest</h1>
        <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setActiveTab("backtest")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === "backtest"
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Single Run
          </button>
          <button
            onClick={() => setActiveTab("walkforward")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === "walkforward"
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Walk-Forward
          </button>
        </div>
      </div>

      <div className="bg-surface rounded-xl border border-border p-4">
        <BacktestForm onResult={setResult} />
      </div>

      {displayMetrics && activeTab === "backtest" && (
        <BacktestResults
          metrics={displayMetrics}
          equityData={sampleEquity}
          drawdownData={sampleDrawdown}
        />
      )}

      {activeTab === "walkforward" && (
        <WalkforwardResults windows={SAMPLE_WALKFORWARD} />
      )}
    </div>
  );
}

function generateSampleEquity() {
  const data: { date: string; equity: number }[] = [];
  let equity = 10000;
  for (let i = 0; i < 120; i++) {
    equity += (Math.random() - 0.42) * 150;
    equity = Math.max(equity, 8000);
    const d = new Date(2024, 0, 1 + i);
    data.push({ date: d.toISOString().slice(0, 10), equity: Math.round(equity) });
  }
  return data;
}

function generateSampleDrawdown() {
  const data: { date: string; drawdown: number }[] = [];
  let peak = 10000;
  let equity = 10000;
  for (let i = 0; i < 120; i++) {
    equity += (Math.random() - 0.42) * 150;
    equity = Math.max(equity, 8000);
    peak = Math.max(peak, equity);
    const dd = ((equity - peak) / peak) * 100;
    const d = new Date(2024, 0, 1 + i);
    data.push({ date: d.toISOString().slice(0, 10), drawdown: Math.round(dd * 100) / 100 });
  }
  return data;
}

const SAMPLE_WALKFORWARD = [
  { window: 1, train_start: "2024-01", train_end: "2024-04", test_start: "2024-04", test_end: "2024-05", sharpe_ratio: 1.8, total_return: 0.12, max_drawdown: 0.06, trades: 12 },
  { window: 2, train_start: "2024-02", train_end: "2024-05", test_start: "2024-05", test_end: "2024-06", sharpe_ratio: 1.4, total_return: 0.08, max_drawdown: 0.09, trades: 9 },
  { window: 3, train_start: "2024-03", train_end: "2024-06", test_start: "2024-06", test_end: "2024-07", sharpe_ratio: 2.1, total_return: 0.18, max_drawdown: 0.04, trades: 14 },
  { window: 4, train_start: "2024-04", train_end: "2024-07", test_start: "2024-07", test_end: "2024-08", sharpe_ratio: 0.9, total_return: -0.03, max_drawdown: 0.12, trades: 8 },
  { window: 5, train_start: "2024-05", train_end: "2024-08", test_start: "2024-08", test_end: "2024-09", sharpe_ratio: 1.6, total_return: 0.14, max_drawdown: 0.05, trades: 11 },
  { window: 6, train_start: "2024-06", train_end: "2024-09", test_start: "2024-09", test_end: "2024-10", sharpe_ratio: 1.3, total_return: 0.06, max_drawdown: 0.08, trades: 10 },
];
