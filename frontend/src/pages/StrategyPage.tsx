import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { evaluateSignal } from "@/api/signals";
import { getUserSettings } from "@/api/settings";
import { useSignalStore } from "@/store/useSignalStore";
import type { SignalStage } from "@/types";
import clsx from "clsx";

const STAGE_COLORS: Record<SignalStage, string> = {
  inactive: "bg-gray-700 text-gray-400",
  setup: "bg-yellow-900/50 text-yellow-400",
  trigger: "bg-blue-900/50 text-blue-400",
  confirmed: "bg-green-900/50 text-profit",
};

export function StrategyPage() {
  const activeSignals = useSignalStore((s) => s.activeSignals);
  const history = useSignalStore((s) => s.history);
  const [symbol] = useState("BTC");

  const { data: settings } = useQuery({
    queryKey: ["userSettings"],
    queryFn: getUserSettings,
  });

  const evaluateMutation = useMutation({
    mutationFn: () =>
      evaluateSignal({
        symbol,
        closes_4h: [],
        closes_1h: [],
        price_15m: 0,
        is_bullish_15m: true,
      }),
  });

  const result = evaluateMutation.data;

  return (
    <div className="space-y-6">
      {/* Strategy Configuration */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-300">RSI Strategy Configuration</h2>
          <button
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluateMutation.isPending}
            className="px-4 py-2 bg-neutral-accent text-white text-xs font-semibold rounded-lg hover:bg-neutral-accent/90 disabled:opacity-50"
          >
            {evaluateMutation.isPending ? "Evaluating..." : "Evaluate Signal"}
          </button>
        </div>

        {settings ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-2 text-xs">
            <ConfigRow label="RSI Period" value={String(settings.rsi_period)} />
            <ConfigRow label="Regime Timeframe" value="4H" />
            <ConfigRow label="Regime Bullish" value={String(settings.rsi_regime_bullish_threshold)} />
            <ConfigRow label="Regime Bearish" value={String(settings.rsi_regime_bearish_threshold)} />
            <ConfigRow label="Signal Timeframe" value="1H" />
            <ConfigRow label="Exit Partial R" value={String(settings.rsi_exit_partial_r)} />
            <ConfigRow label="Exit Breakeven R" value={String(settings.rsi_exit_breakeven_r)} />
            <ConfigRow label="Exit Max Hours" value={String(settings.rsi_exit_max_hours)} />
          </div>
        ) : (
          <div className="text-center py-4 text-gray-600 text-xs">Loading configuration...</div>
        )}
      </div>

      {/* Current Evaluation Result */}
      {result && (
        <div className="bg-surface rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Latest Evaluation</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <span className="text-xs text-gray-500 block">Regime</span>
              <span className={`text-sm font-semibold ${result.regime === "bullish" ? "text-profit" : result.regime === "bearish" ? "text-loss" : "text-neutral-accent"}`}>
                {result.regime?.toUpperCase() ?? "N/A"}
              </span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">RSI 4H</span>
              <span className="text-sm font-mono text-white">{result.rsi_4h?.toFixed(1) ?? "N/A"}</span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">RSI 1H</span>
              <span className="text-sm font-mono text-white">{result.rsi_1h?.toFixed(1) ?? "N/A"}</span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">Signal</span>
              <span className="text-sm font-semibold text-white">
                {result.signal
                  ? `${result.signal.signal_type.toUpperCase()} (${result.signal.stage})`
                  : "None"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Active Signals */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Active Signals</h2>
        {activeSignals.length === 0 ? (
          <div className="text-center py-6 text-gray-600 text-xs">No active signals</div>
        ) : (
          <div className="space-y-2">
            {activeSignals.map((sig) => (
              <div
                key={sig.id}
                className="flex items-center justify-between bg-gray-800/50 rounded-lg p-3"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={clsx(
                      "text-xs font-bold px-2 py-0.5 rounded",
                      sig.type === "long" ? "text-profit bg-green-900/30" : "text-loss bg-red-900/30"
                    )}
                  >
                    {sig.type.toUpperCase()}
                  </span>
                  <span className="text-xs text-gray-400">
                    RSI 1H: {sig.rsi_1h.toFixed(1)} | RSI 4H: {sig.rsi_4h.toFixed(1)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <StrengthBar value={sig.strength} />
                  <span
                    className={clsx(
                      "text-[10px] px-1.5 py-0.5 rounded",
                      STAGE_COLORS[sig.stage as SignalStage]
                    )}
                  >
                    {sig.stage}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* RSI Multi-Timeframe Chart */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300">RSI Multi-Timeframe</h2>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-blue-500 inline-block" /> 4H</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-500 inline-block" /> 1H</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-gray-500 inline-block" /> 15m</span>
          </div>
        </div>
        <div className="text-center py-12 text-gray-600 text-xs">
          RSI data will appear when the market data feed is connected.
        </div>
      </div>

      {/* Signal History */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Signal History</h2>
        {history.length === 0 ? (
          <div className="text-center py-6 text-gray-600 text-xs">
            No signal history yet. Signals will appear when the bot evaluates market conditions.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 uppercase border-b border-border">
                  <th className="text-left py-2 px-2">Time</th>
                  <th className="text-left py-2 px-2">Type</th>
                  <th className="text-left py-2 px-2">Regime</th>
                  <th className="text-right py-2 px-2">RSI 1H</th>
                  <th className="text-right py-2 px-2">RSI 4H</th>
                  <th className="text-right py-2 px-2">Price</th>
                  <th className="text-right py-2 px-2">Strength</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 20).map((sig) => (
                  <tr key={sig.id} className="border-b border-border/50 hover:bg-gray-800/30">
                    <td className="py-2 px-2 text-gray-400">
                      {new Date(sig.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td className="py-2 px-2">
                      <span className={sig.type === "long" ? "text-profit font-semibold" : "text-loss font-semibold"}>
                        {sig.type.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <span className={
                        sig.regime === "bullish" ? "text-profit" : sig.regime === "bearish" ? "text-loss" : "text-neutral-accent"
                      }>
                        {sig.regime}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right font-mono text-gray-300">{sig.rsi_1h.toFixed(1)}</td>
                    <td className="py-2 px-2 text-right font-mono text-gray-300">{sig.rsi_4h.toFixed(1)}</td>
                    <td className="py-2 px-2 text-right font-mono text-gray-300">${sig.price.toFixed(0)}</td>
                    <td className="py-2 px-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <div className="w-12 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${sig.strength > 0.6 ? "bg-profit" : sig.strength > 0.3 ? "bg-yellow-500" : "bg-loss"}`}
                            style={{ width: `${sig.strength * 100}%` }}
                          />
                        </div>
                        <span className="text-gray-400 w-8 text-right">{(sig.strength * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1 border-b border-border/50">
      <span className="text-gray-500">{label}</span>
      <span className="text-white font-mono">{value}</span>
    </div>
  );
}

function StrengthBar({ value }: { value: number }) {
  const color = value > 0.6 ? "bg-profit" : value > 0.3 ? "bg-yellow-500" : "bg-loss";
  return (
    <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${value * 100}%` }} />
    </div>
  );
}
