import { get } from "./client";

export interface MarketTicker {
  symbol: string;
  mid_price: number;
}

export interface MarketResponse {
  tickers: MarketTicker[];
  count: number;
}

export function getMarketData() {
  return get<MarketResponse>("/v1/market");
}
