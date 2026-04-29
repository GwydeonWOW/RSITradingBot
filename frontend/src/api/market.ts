import { get } from "./client";

export interface MarketTicker {
  symbol: string;
  mid_price: number;
  mark_price: number;
  prev_day_px: number;
  day_ntl_vlm: number;
  funding: number;
  open_interest: number;
}

export interface MarketResponse {
  tickers: MarketTicker[];
  count: number;
}

export function getMarketData() {
  return get<MarketResponse>("/v1/market");
}
