import { create } from "zustand";
import type { SignalHistoryEntry, SignalType, SignalStage, Regime } from "@/types";

interface SignalState {
  activeSignals: SignalHistoryEntry[];
  history: SignalHistoryEntry[];
  addActiveSignal: (signal: Omit<SignalHistoryEntry, "id">) => void;
  moveToHistory: (id: string) => void;
  clearActives: () => void;
}

let idCounter = 0;

export const useSignalStore = create<SignalState>((set) => ({
  activeSignals: [],
  history: generateSampleHistory(),
  addActiveSignal: (signal) =>
    set((state) => ({
      activeSignals: [
        { ...signal, id: `sig_${++idCounter}` },
        ...state.activeSignals,
      ],
    })),
  moveToHistory: (id) =>
    set((state) => {
      const signal = state.activeSignals.find((s) => s.id === id);
      if (!signal) return state;
      return {
        activeSignals: state.activeSignals.filter((s) => s.id !== id),
        history: [signal, ...state.history],
      };
    }),
  clearActives: () => set({ activeSignals: [] }),
}));

function generateSampleHistory(): SignalHistoryEntry[] {
  const entries: SignalHistoryEntry[] = [];
  const types: SignalType[] = ["long", "short"];
  const stages: SignalStage[] = ["confirmed"];
  const regimes: Regime[] = ["bullish", "bearish"];

  for (let i = 0; i < 20; i++) {
    const type = types[i % 2]!;
    const regime = regimes[i % 2]!;
    const date = new Date(Date.now() - i * 3600000 * 4);
    entries.push({
      id: `hist_${i}`,
      timestamp: date.toISOString(),
      type,
      stage: stages[0]!,
      regime,
      rsi_1h: type === "long" ? 44 + Math.random() * 4 : 54 + Math.random() * 6,
      rsi_4h: regime === "bullish" ? 56 + Math.random() * 10 : 35 + Math.random() * 10,
      price: 94000 + Math.random() * 2000,
      strength: 0.4 + Math.random() * 0.6,
    });
  }
  return entries;
}
