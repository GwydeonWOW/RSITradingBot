import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { evaluateSignal, getBotStatus, getBotLogs } from "@/api/signals";
import { getUserSettings } from "@/api/settings";
import { RSIWidget } from "@/components/market/RSIWidget";
import type { SignalStage, BotLogEntry } from "@/types";
import clsx from "clsx";

const STAGE_COLORS: Record<SignalStage, string> = {
  inactive: "bg-gray-700 text-gray-400",
  setup: "bg-yellow-900/50 text-yellow-400",
  trigger: "bg-blue-900/50 text-blue-400",
  confirmed: "bg-green-900/50 text-profit",
};

export function StrategyPage() {
  const [symbol] = useState("BTC");

  const { data: settings } = useQuery({
    queryKey: ["userSettings"],
    queryFn: getUserSettings,
  });

  const { data: bot } = useQuery({
    queryKey: ["botStatus"],
    queryFn: getBotStatus,
    refetchInterval: 5000,
  });

  const { data: logsData } = useQuery({
    queryKey: ["botLogs"],
    queryFn: getBotLogs,
    refetchInterval: 10000,
  });

  const evaluateMutation = useMutation({
    mutationFn: () => evaluateSignal({ symbol }),
  });

  const result = evaluateMutation.data;
  const signalLogs = (logsData?.logs ?? []).filter(
    (l: BotLogEntry) => l.signal_type && l.signal_type !== "none"
  );

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
                {(result.regime ?? "N/A").toUpperCase()}
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
                  ? `${result.signal.type.toUpperCase()} (${result.signal.stage})`
                  : "None"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Active Signal */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Active Signal</h2>
        {bot && bot.signal_stage && bot.signal_stage !== "inactive" && bot.signal_type ? (
          <div className="flex items-center justify-between bg-gray-800/50 rounded-lg p-3">
            <div className="flex items-center gap-3">
              <span
                className={clsx(
                  "text-xs font-bold px-2 py-0.5 rounded",
                  bot.signal_type === "long" ? "text-profit bg-green-900/30" : "text-loss bg-red-900/30"
                )}
              >
                {bot.signal_type.toUpperCase()}
              </span>
              <span className="text-xs text-gray-400">
                RSI 1H: {bot.rsi_1h?.toFixed(1) ?? "—"} | RSI 4H: {bot.rsi_4h?.toFixed(1) ?? "—"}
              </span>
            </div>
            <span
              className={clsx(
                "text-[10px] px-1.5 py-0.5 rounded",
                STAGE_COLORS[bot.signal_stage as SignalStage]
              )}
            >
              {bot.signal_stage}
            </span>
          </div>
        ) : (
          <div className="text-center py-6 text-gray-600 text-xs">
            {bot?.running ? "No active signal — monitoring market conditions." : "Start the bot to detect signals."}
          </div>
        )}
      </div>

      {/* RSI Multi-Timeframe */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300">RSI Multi-Timeframe</h2>
          {bot?.last_eval_at && (
            <span className="text-[10px] text-gray-500">
              Updated {new Date(bot.last_eval_at).toLocaleTimeString()}
            </span>
          )}
        </div>
        {bot && (bot.rsi_4h != null || bot.rsi_1h != null) ? (
          <div className="flex items-center justify-center gap-8 py-4">
            <RSIWidget label="4H" value={bot.rsi_4h ?? 0} />
            <RSIWidget label="1H" value={bot.rsi_1h ?? 0} />
          </div>
        ) : (
          <div className="text-center py-12 text-gray-600 text-xs">
            {bot?.running ? "Waiting for first evaluation cycle..." : "Start the bot to see live RSI data."}
          </div>
        )}
        {bot && (bot.rsi_4h != null || bot.rsi_1h != null) && (
          <div className="mt-3 pt-3 border-t border-border/50 grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-gray-500">Regime</span>
              <span className={`block text-sm font-semibold ${bot.regime === "bullish" ? "text-profit" : bot.regime === "bearish" ? "text-loss" : "text-neutral-accent"}`}>
                {(bot.regime ?? "N/A").toUpperCase()}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Last Price</span>
              <span className="block text-sm font-mono text-white">
                {bot.last_price != null ? `$${bot.last_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "N/A"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Signal History — from bot logs */}
      <div className="bg-surface rounded-xl border border-border p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Signal History</h2>
        {signalLogs.length === 0 ? (
          <div className="text-center py-6 text-gray-600 text-xs">
            {bot?.running ? "Monitoring — signal events will appear here as they occur." : "Start the bot to generate signal history."}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 uppercase border-b border-border">
                  <th className="text-left py-2 px-2">Time</th>
                  <th className="text-left py-2 px-2">Type</th>
                  <th className="text-left py-2 px-2">Stage</th>
                  <th className="text-left py-2 px-2">Regime</th>
                  <th className="text-right py-2 px-2">RSI 1H</th>
                  <th className="text-right py-2 px-2">RSI 4H</th>
                  <th className="text-right py-2 px-2">Price</th>
                </tr>
              </thead>
              <tbody>
                {signalLogs.map((l: BotLogEntry) => (
                  <tr key={l.id} className="border-b border-border/50 hover:bg-gray-800/30">
                    <td className="py-2 px-2 text-gray-400">
                      {new Date(l.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </td>
                    <td className="py-2 px-2">
                      <span className={l.signal_type === "long" ? "text-profit font-semibold" : "text-loss font-semibold"}>
                        {l.signal_type?.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <span className={clsx("text-[10px] px-1.5 py-0.5 rounded", STAGE_COLORS[(l.signal_stage ?? "inactive") as SignalStage])}>
                        {l.signal_stage}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <span className={
                        l.regime === "bullish" ? "text-profit" : l.regime === "bearish" ? "text-loss" : "text-neutral-accent"
                      }>
                        {l.regime ?? "—"}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right font-mono text-gray-300">{l.rsi_1h?.toFixed(1) ?? "—"}</td>
                    <td className="py-2 px-2 text-right font-mono text-gray-300">{l.rsi_4h?.toFixed(1) ?? "—"}</td>
                    <td className="py-2 px-2 text-right font-mono text-gray-300">{l.price != null ? `$${l.price.toLocaleString()}` : "—"}</td>
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

