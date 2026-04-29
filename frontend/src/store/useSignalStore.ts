import { create } from "zustand";
import type { SignalHistoryEntry } from "@/types";

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
  history: [],
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
