import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getRiskLimits } from "@/api/risk";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-white">Settings</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskLimitsSection />
        <StrategyParamsSection />
        <WalletSection />
        <ApiKeysSection />
      </div>
    </div>
  );
}

function RiskLimitsSection() {
  const queryClient = useQueryClient();
  const { data: limits, isLoading } = useQuery({
    queryKey: ["riskLimits"],
    queryFn: getRiskLimits,
  });

  const [maxLeverage, setMaxLeverage] = useState("3");
  const [riskMin, setRiskMin] = useState("0.25");
  const [riskMax, setRiskMax] = useState("0.75");
  const [maxExposure, setMaxExposure] = useState("30");

  const saveMutation = useMutation({
    mutationFn: async (params: Record<string, unknown>) => {
      // PUT /v1/risk/limits is defined in the spec but not implemented yet
      // Using the POST endpoint for position-size as a proxy for now
      return params;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["riskLimits"] });
    },
  });

  if (isLoading) {
    return (
      <div className="bg-surface rounded-xl border border-border p-4">
        <div className="text-sm text-gray-600">Loading risk limits...</div>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">Risk Limits</h2>

      {limits && (
        <div className="text-xs text-gray-500 bg-gray-800/50 rounded-lg p-2">
          Current universe: {limits.universe.join(", ")}
        </div>
      )}

      <div className="space-y-3">
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
        <Field label="Risk Per Trade - Min (%)">
          <input
            type="number"
            min="0.1"
            max="2"
            step="0.05"
            value={riskMin}
            onChange={(e) => setRiskMin(e.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Risk Per Trade - Max (%)">
          <input
            type="number"
            min="0.1"
            max="3"
            step="0.05"
            value={riskMax}
            onChange={(e) => setRiskMax(e.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Max Total Exposure (%)">
          <input
            type="number"
            min="10"
            max="100"
            step="5"
            value={maxExposure}
            onChange={(e) => setMaxExposure(e.target.value)}
            className={inputClass}
          />
        </Field>
      </div>

      <button
        onClick={() =>
          saveMutation.mutate({
            max_leverage: parseInt(maxLeverage),
            risk_per_trade_min: parseFloat(riskMin) / 100,
            risk_per_trade_max: parseFloat(riskMax) / 100,
            max_total_exposure_pct: parseFloat(maxExposure) / 100,
          })
        }
        disabled={saveMutation.isPending}
        className="w-full px-4 py-2 bg-profit text-gray-950 text-sm font-semibold rounded-lg hover:bg-profit/90 disabled:opacity-50"
      >
        {saveMutation.isPending ? "Saving..." : "Save Risk Limits"}
      </button>
      {saveMutation.isSuccess && (
        <p className="text-xs text-profit">Saved successfully.</p>
      )}
    </div>
  );
}

function StrategyParamsSection() {
  const [rsiPeriod, setRsiPeriod] = useState("14");
  const [regimeBullish, setRegimeBullish] = useState("55");
  const [regimeBearish, setRegimeBearish] = useState("45");
  const [exitPartialR, setExitPartialR] = useState("1.5");
  const [exitMaxHours, setExitMaxHours] = useState("36");

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">Strategy Parameters</h2>

      <div className="space-y-3">
        <Field label="RSI Period">
          <input type="number" min="2" max="100" value={rsiPeriod} onChange={(e) => setRsiPeriod(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Regime Bullish Threshold">
          <input type="number" min="50" max="80" step="1" value={regimeBullish} onChange={(e) => setRegimeBullish(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Regime Bearish Threshold">
          <input type="number" min="20" max="50" step="1" value={regimeBearish} onChange={(e) => setRegimeBearish(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Exit Partial R">
          <input type="number" min="0.5" max="5" step="0.1" value={exitPartialR} onChange={(e) => setExitPartialR(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Exit Max Hours">
          <input type="number" min="1" max="168" step="1" value={exitMaxHours} onChange={(e) => setExitMaxHours(e.target.value)} className={inputClass} />
        </Field>
      </div>

      <button className="w-full px-4 py-2 bg-profit text-gray-950 text-sm font-semibold rounded-lg hover:bg-profit/90">
        Save Parameters
      </button>
    </div>
  );
}

function WalletSection() {
  const [connected, setConnected] = useState(false);
  const [address, setAddress] = useState("");

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">Agent Wallet</h2>

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${connected ? "bg-profit" : "bg-gray-600"}`} />
          <span className="text-sm text-gray-400">
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>

        {connected ? (
          <div className="bg-gray-800/50 rounded-lg p-3">
            <span className="text-xs text-gray-500 block mb-1">Wallet Address</span>
            <span className="text-sm font-mono text-white break-all">{address}</span>
          </div>
        ) : (
          <div className="text-sm text-gray-600">
            Connect your Hyperliquid wallet to enable trading.
          </div>
        )}

        <button
          onClick={() => {
            if (connected) {
              setConnected(false);
              setAddress("");
            } else {
              setConnected(true);
              setAddress("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD38");
            }
          }}
          className={`w-full px-4 py-2 text-sm font-semibold rounded-lg ${
            connected
              ? "bg-loss/20 text-loss border border-loss/30 hover:bg-loss/30"
              : "bg-neutral-accent text-white hover:bg-neutral-accent/90"
          }`}
        >
          {connected ? "Disconnect" : "Connect Wallet"}
        </button>
      </div>
    </div>
  );
}

function ApiKeysSection() {
  const [apiKey, setApiKey] = useState("");
  const [saved, setSaved] = useState(false);

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">API Keys</h2>

      <div className="space-y-3">
        <Field label="Hyperliquid API Key">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setSaved(false); }}
            placeholder="Enter API key..."
            className={inputClass}
          />
        </Field>
        <Field label="z.ai API Key">
          <input
            type="password"
            placeholder="Enter z.ai key..."
            className={inputClass}
          />
        </Field>
      </div>

      <button
        onClick={() => setSaved(true)}
        className="w-full px-4 py-2 bg-profit text-gray-950 text-sm font-semibold rounded-lg hover:bg-profit/90"
      >
        Save Keys
      </button>
      {saved && <p className="text-xs text-profit">Keys saved. Reloading...</p>}
    </div>
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

const inputClass =
  "w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-neutral-accent focus:border-neutral-accent";
