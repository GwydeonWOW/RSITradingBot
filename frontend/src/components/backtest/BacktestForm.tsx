import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { runBacktest } from "@/api/strategies";
import type { BacktestRequest } from "@/types";

interface Props {
  onResult: (result: { result_id: string; total_trades: number }) => void;
}

export function BacktestForm({ onResult }: Props) {
  const [symbol, setSymbol] = useState("BTC");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [equity, setEquity] = useState("10000");
  const [rsiPeriod, setRsiPeriod] = useState("14");
  const [regimeBullish, setRegimeBullish] = useState("55");
  const [regimeBearish, setRegimeBearish] = useState("45");
  const [riskPerTrade, setRiskPerTrade] = useState("0.005");
  const [maxLeverage, setMaxLeverage] = useState("3");
  const [commission] = useState("0.0005");

  const mutation = useMutation({
    mutationFn: (req: BacktestRequest) => runBacktest(req),
    onSuccess: (data) => {
      onResult(data);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const eq = parseFloat(equity);
    if (isNaN(eq) || eq <= 0) return;

    mutation.mutate({
      symbol,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      equity: eq,
      params: {
        rsi_period: parseInt(rsiPeriod) || 14,
        regime_bullish: parseFloat(regimeBullish) || 55,
        regime_bearish: parseFloat(regimeBearish) || 45,
        risk_per_trade: parseFloat(riskPerTrade) || 0.005,
        max_leverage: parseInt(maxLeverage) || 3,
        commission: parseFloat(commission) || 0.0005,
      },
    });
  }

  const inputClass =
    "w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-neutral-accent focus:border-neutral-accent";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Field label="Symbol">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className={inputClass}
          >
            <option value="BTC">BTC</option>
            <option value="ETH">ETH</option>
            <option value="SOL">SOL</option>
          </select>
        </Field>

        <Field label="Start Date">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="End Date">
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="Initial Equity ($)">
          <input
            type="number"
            min="100"
            step="100"
            value={equity}
            onChange={(e) => setEquity(e.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="RSI Period">
          <input
            type="number"
            min="2"
            max="100"
            value={rsiPeriod}
            onChange={(e) => setRsiPeriod(e.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="Max Leverage">
          <input
            type="number"
            min="1"
            max="10"
            value={maxLeverage}
            onChange={(e) => setMaxLeverage(e.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="Regime Bullish Threshold">
          <input
            type="number"
            min="50"
            max="80"
            step="1"
            value={regimeBullish}
            onChange={(e) => setRegimeBullish(e.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="Regime Bearish Threshold">
          <input
            type="number"
            min="20"
            max="50"
            step="1"
            value={regimeBearish}
            onChange={(e) => setRegimeBearish(e.target.value)}
            className={inputClass}
          />
        </Field>

        <Field label="Risk Per Trade">
          <input
            type="number"
            min="0.001"
            max="0.02"
            step="0.001"
            value={riskPerTrade}
            onChange={(e) => setRiskPerTrade(e.target.value)}
            className={inputClass}
          />
        </Field>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-6 py-2.5 bg-profit text-gray-950 font-semibold text-sm rounded-lg hover:bg-profit/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {mutation.isPending ? "Running..." : "Run Backtest"}
        </button>

        {mutation.isError && (
          <span className="text-sm text-loss">
            {(mutation.error as Error).message}
          </span>
        )}
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-gray-500 uppercase mb-1">{label}</label>
      {children}
    </div>
  );
}
