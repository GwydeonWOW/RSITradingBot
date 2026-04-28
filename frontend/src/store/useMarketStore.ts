import { create } from "zustand";
import type { MarketData, Regime } from "@/types";

interface MarketState {
  markets: Record<string, MarketData>;
  updateMarket: (data: MarketData) => void;
  setRegime: (symbol: string, regime: Regime) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  markets: {
    BTC: {
      symbol: "BTC",
      markPrice: 94500,
      spread: 0.01,
      rsi_4h: 58.2,
      rsi_1h: 44.5,
      rsi_15m: 51.3,
      regime: "bullish",
      bidSize: 12.5,
      askSize: 8.3,
      lastUpdate: Date.now(),
    },
    ETH: {
      symbol: "ETH",
      markPrice: 3650,
      spread: 0.02,
      rsi_4h: 42.1,
      rsi_1h: 55.8,
      rsi_15m: 48.9,
      regime: "bearish",
      bidSize: 45.2,
      askSize: 32.1,
      lastUpdate: Date.now(),
    },
    SOL: {
      symbol: "SOL",
      markPrice: 152.8,
      spread: 0.03,
      rsi_4h: 50.0,
      rsi_1h: 50.0,
      rsi_15m: 50.0,
      regime: "neutral",
      bidSize: 200,
      askSize: 180,
      lastUpdate: Date.now(),
    },
  },
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
