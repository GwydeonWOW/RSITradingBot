import { create } from "zustand";
import type { MarketData, Regime } from "@/types";

interface MarketState {
  markets: Record<string, MarketData>;
  updateMarket: (data: MarketData) => void;
  setRegime: (symbol: string, regime: Regime) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  markets: {},
  updateMarket: (data) =>
    set((state) => ({
      markets: {
        ...state.markets,
        [data.symbol]: { ...data, lastUpdate: Date.now() },
      },
    })),
  setRegime: (symbol, regime) =>
    set((state) => {
      const existing = state.markets[symbol];
      if (!existing) return state;
      return {
        markets: {
          ...state.markets,
          [symbol]: { ...existing, regime },
        },
      };
    }),
}));
