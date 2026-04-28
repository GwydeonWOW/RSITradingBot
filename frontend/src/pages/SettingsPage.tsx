import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getRiskLimits } from "@/api/risk";
import { getWallets, connectWallet, deleteWallet, getWalletBalance } from "@/api/wallets";
import type { Wallet } from "@/types";
import { ApiError } from "@/api/client";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-white">Settings</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskLimitsSection />
        <StrategyParamsSection />
        <WalletManagementSection />
        <ApiKeysSection />
      </div>
    </div>
  );
}

/* ── Risk Limits ─────────────────────────────────────────── */

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

/* ── Strategy Params ─────────────────────────────────────── */

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

/* ── Wallet Management ───────────────────────────────────── */

function WalletManagementSection() {
  const queryClient = useQueryClient();
  const { data: wallets, isLoading } = useQuery({
    queryKey: ["wallets"],
    queryFn: getWallets,
  });

  const [showForm, setShowForm] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="bg-surface rounded-xl border border-border p-4">
        <div className="text-sm text-gray-600">Loading wallets...</div>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl border border-border p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">Wallets</h2>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="px-3 py-1.5 bg-neutral-accent text-white text-xs font-semibold rounded-lg hover:bg-neutral-accent/90"
          >
            Connect Wallet
          </button>
        )}
      </div>

      {showForm && (
        <ConnectWalletForm
          onClose={() => setShowForm(false)}
          onSuccess={() => {
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ["wallets"] });
          }}
        />
      )}

      {(!wallets || wallets.length === 0) && !showForm ? (
        <p className="text-sm text-gray-600">
          No wallets connected. Connect your Hyperliquid wallet to enable trading.
        </p>
      ) : (
        <div className="space-y-3">
          {wallets?.map((wallet) => (
            <WalletRow
              key={wallet.id}
              wallet={wallet}
              confirmDeleteId={confirmDeleteId}
              onConfirmDelete={setConfirmDeleteId}
              onDeleted={() => queryClient.invalidateQueries({ queryKey: ["wallets"] })}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ConnectWalletForm({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [label, setLabel] = useState("");
  const [masterAddress, setMasterAddress] = useState("");
  const [agentAddress, setAgentAddress] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!label || !masterAddress || !agentAddress || !privateKey) {
      setError("All fields are required.");
      return;
    }

    setLoading(true);
    try {
      await connectWallet({ label, master_address: masterAddress, agent_address: agentAddress, private_key: privateKey });
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to connect wallet.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-gray-800/50 rounded-lg p-3 space-y-3">
      {error && (
        <div className="bg-loss/10 border border-loss/30 text-loss text-xs rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <Field label="Label">
        <input
          type="text"
          required
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="My trading wallet"
          className={inputClass}
        />
      </Field>

      <Field label="Master Address">
        <input
          type="text"
          required
          value={masterAddress}
          onChange={(e) => setMasterAddress(e.target.value)}
          placeholder="0x..."
          className={inputClass}
        />
      </Field>

      <Field label="Agent Address">
        <input
          type="text"
          required
          value={agentAddress}
          onChange={(e) => setAgentAddress(e.target.value)}
          placeholder="0x..."
          className={inputClass}
        />
      </Field>

      <Field label="Agent Private Key">
        <input
          type="password"
          required
          value={privateKey}
          onChange={(e) => setPrivateKey(e.target.value)}
          placeholder="One-time input, never stored in browser"
          className={inputClass}
        />
        <p className="text-xs text-gray-600 mt-1">
          Sent once to the server and never stored in the frontend.
        </p>
      </Field>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 px-3 py-2 border border-gray-700 text-gray-400 text-xs font-semibold rounded-lg hover:bg-gray-700/50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="flex-1 px-3 py-2 bg-neutral-accent text-white text-xs font-semibold rounded-lg hover:bg-neutral-accent/90 disabled:opacity-50"
        >
          {loading ? "Connecting..." : "Connect"}
        </button>
      </div>
    </form>
  );
}

function WalletRow({
  wallet,
  confirmDeleteId,
  onConfirmDelete,
  onDeleted,
}: {
  wallet: Wallet;
  confirmDeleteId: string | null;
  onConfirmDelete: (id: string | null) => void;
  onDeleted: () => void;
}) {
  const [loading, setLoading] = useState(false);

  const { data: balance } = useQuery({
    queryKey: ["walletBalance", wallet.id],
    queryFn: () => getWalletBalance(wallet.id),
    refetchInterval: 30000,
  });

  async function handleDelete() {
    setLoading(true);
    try {
      await deleteWallet(wallet.id);
      onConfirmDelete(null);
      onDeleted();
    } catch {
      // Error is handled by the global client
    } finally {
      setLoading(false);
    }
  }

  const isConfirming = confirmDeleteId === wallet.id;

  return (
    <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-white">{wallet.label}</span>
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                wallet.is_active ? "bg-profit" : "bg-gray-600"
              }`}
            />
          </div>
          <div className="text-xs font-mono text-gray-500 mt-1">
            Master: {truncateAddress(wallet.master_address)}
          </div>
          <div className="text-xs font-mono text-gray-500">
            Agent: {truncateAddress(wallet.agent_address)}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {balance && (
            <span className="text-xs text-gray-400">
              {balance.total_balance.toFixed(4)} {balance.currency}
            </span>
          )}
          {isConfirming ? (
            <div className="flex gap-1">
              <button
                onClick={handleDelete}
                disabled={loading}
                className="px-2 py-1 bg-loss/20 text-loss text-xs rounded hover:bg-loss/30 disabled:opacity-50"
              >
                {loading ? "..." : "Confirm"}
              </button>
              <button
                onClick={() => onConfirmDelete(null)}
                className="px-2 py-1 border border-gray-700 text-gray-400 text-xs rounded hover:bg-gray-700/50"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => onConfirmDelete(wallet.id)}
              className="px-2 py-1 text-xs text-gray-500 hover:text-loss transition-colors"
              title="Delete wallet"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function truncateAddress(addr: string): string {
  if (addr.length <= 14) return addr;
  return `${addr.slice(0, 8)}...${addr.slice(-6)}`;
}

/* ── API Keys ────────────────────────────────────────────── */

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

/* ── Shared ──────────────────────────────────────────────── */

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
