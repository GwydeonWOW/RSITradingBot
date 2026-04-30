import { useQuery } from "@tanstack/react-query";
import { getBotStatus } from "@/api/signals";

export function RiskPanel() {
  const { data: bot } = useQuery({
    queryKey: ["botStatus"],
    queryFn: getBotStatus,
    refetchInterval: 30000,
  });

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">Risk</h2>
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${bot?.running ? "bg-profit animate-pulse" : "bg-gray-600"}`} />
          <span className="text-[10px] text-gray-500">{bot?.running ? "Bot Active" : "Bot Idle"}</span>
        </div>
      </div>

      {bot && bot.last_eval_at ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-500">Regime</span>
              <span className={`block font-semibold ${bot.regime === "bullish" ? "text-profit" : bot.regime === "bearish" ? "text-loss" : "text-gray-400"}`}>
                {(bot.regime ?? "N/A").toUpperCase()}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Signal</span>
              <span className="block font-semibold text-white">
                {bot.signal_stage !== "inactive" ? `${(bot.signal_type ?? "").toUpperCase()} (${bot.signal_stage})` : "None"}
              </span>
            </div>
            <div>
              <span className="text-gray-500">RSI 4H</span>
              <span className="block font-mono text-white">{bot.rsi_4h?.toFixed(1) ?? "—"}</span>
            </div>
            <div>
              <span className="text-gray-500">RSI 1H</span>
              <span className="block font-mono text-white">{bot.rsi_1h?.toFixed(1) ?? "—"}</span>
            </div>
            <div>
              <span className="text-gray-500">Positions</span>
              <span className="block font-mono text-white">{bot.open_positions}</span>
            </div>
            <div>
              <span className="text-gray-500">Last Eval</span>
              <span className="block font-mono text-gray-400">
                {bot.last_eval_at ? new Date(bot.last_eval_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
              </span>
            </div>
          </div>
          {bot.last_error && (
            <div className="text-[10px] text-loss bg-red-900/20 rounded p-1.5">
              {bot.last_error}
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-6 text-gray-600 text-xs">
          {bot?.running ? "Waiting for first evaluation..." : "Bot not running."}
        </div>
      )}
    </div>
  );
}
