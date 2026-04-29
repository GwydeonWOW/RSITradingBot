import { create } from "zustand";
import type { MarketTicker } from "@/api/market";

interface MarketState {
  tickers: Record<string, MarketTicker>;
  lastUpdate: number;
  setTickers: (tickers: MarketTicker[]) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  tickers: {},
  lastUpdate: 0,
  setTickers: (list) =>
    set({
      tickers: Object.fromEntries(list.map((t) => [t.symbol, t])),
      lastUpdate: Date.now(),
    }),
}));
