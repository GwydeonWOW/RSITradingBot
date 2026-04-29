import { get, put } from "./client";

export interface UserSettings {
  rsi_period: number;
  rsi_regime_bullish_threshold: number;
  rsi_regime_bearish_threshold: number;
  rsi_signal_long_pullback_low: number;
  rsi_signal_long_pullback_high: number;
  rsi_signal_long_reclaim: number;
  rsi_signal_short_bounce_low: number;
  rsi_signal_short_bounce_high: number;
  rsi_signal_short_lose: number;
  rsi_exit_partial_r: number;
  rsi_exit_breakeven_r: number;
  rsi_exit_max_hours: number;
  risk_per_trade_min: number;
  risk_per_trade_max: number;
  max_leverage: number;
  max_total_exposure_pct: number;
  universe: string[];
  has_zai_api_key: boolean;
  zai_api_key?: string;
}

/** Body for PUT /v1/settings - universe is sent as comma-separated string. */
export type UpdateUserSettings = Omit<Partial<UserSettings>, "universe" | "has_zai_api_key"> & {
  universe?: string;
};

export function getUserSettings() {
  return get<UserSettings>("/v1/settings");
}

export function updateUserSettings(data: UpdateUserSettings) {
  return put<UserSettings>("/v1/settings", data);
}
