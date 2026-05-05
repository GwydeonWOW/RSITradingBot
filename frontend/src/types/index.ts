// ─── Auth & Wallet types ─────────────────────────────────

export interface User {
  id: string;
  email: string;
  display_name: string | null;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface Wallet {
  id: string;
  label: string;
  master_address: string | null;
  agent_address: string;
  is_active: boolean;
  created_at: string;
}

export interface WalletBalance {
  queried_address: string;
  used_master: boolean;
  account_value: number;
  total_raw_usd: number;
  margin_used: number;
  withdrawable: number;
  unrealized_pnl: number;
  spot_usdc: number;
  is_unified: boolean;
  portfolio_value: number;
}

export interface ConnectWalletRequest {
  label: string;
  agent_address: string;
  private_key: string;
  master_address?: string;
}

// ─── Enums ───────────────────────────────────────────────

export type OrderSide = "buy" | "sell";
export type OrderType = "market" | "limit" | "stop_market" | "stop_limit";
export type OrderStatus =
  | "intent"
  | "accepted"
  | "resting"
  | "filling"
  | "filled"
  | "canceled"
  | "rejected"
  | "expired";

export type SignalType = "long" | "short" | "none";
export type SignalStage = "inactive" | "setup" | "trigger" | "confirmed";
export type Regime = "bullish" | "bearish" | "neutral";

// ─── API Request / Response types ────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
}

export interface BacktestRequest {
  symbol: string;
  start_date?: string;
  end_date?: string;
  equity: number;
  params: {
    rsi_period?: number;
    regime_bullish?: number;
    regime_bearish?: number;
    risk_per_trade?: number;
    max_leverage?: number;
    commission?: number;
  };
}

export interface WalkForwardRequest {
  symbol: string;
  start_date?: string;
  end_date?: string;
  equity: number;
  train_bars: number;
  test_bars: number;
  step_bars: number;
  params: Record<string, unknown>;
}

export interface BacktestResponse {
  result_id: string;
  total_trades: number;
  metrics: BacktestMetrics;
}

export interface BacktestMetrics {
  total_return: number;
  cagr: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
}

export interface BacktestDetailResponse {
  result_id: string;
  metrics: BacktestMetrics;
  total_fees: number;
  trade_count: number;
}

export interface BacktestListItem {
  result_id: string;
  symbol: string;
  status: string;
  created_at: string;
}

export interface BacktestListResponse {
  results: BacktestListItem[];
  count: number;
}

export interface SignalEvaluateRequest {
  symbol?: string;
}

export interface SignalEvaluateResponse {
  regime: string | null;
  rsi_4h: number | null;
  rsi_1h: number | null;
  signal: { type: string; stage: string; strength?: number } | null;
  sizing: { notional: number; contracts: number; leverage: number; risk_amount: number } | null;
}

export interface SymbolState {
  symbol: string;
  regime: string | null;
  signal_stage: string | null;
  signal_type: string | null;
  rsi_4h: number | null;
  rsi_1h: number | null;
  last_price: number | null;
  last_eval_at: string | null;
}

export interface BotStatusResponse {
  running: boolean;
  regime: string | null;
  signal_stage: string | null;
  signal_type: string | null;
  rsi_4h: number | null;
  rsi_1h: number | null;
  last_price: number | null;
  last_eval_at: string | null;
  open_positions: number;
  last_error: string | null;
  symbols: SymbolState[];
}

export interface BotLogEntry {
  id: string;
  level: string;
  message: string;
  symbol: string;
  regime: string | null;
  rsi_4h: number | null;
  rsi_1h: number | null;
  price: number | null;
  signal_stage: string | null;
  signal_type: string | null;
  created_at: string;
}

export interface BotLogResponse {
  logs: BotLogEntry[];
  count: number;
}

export interface SignalData {
  signal_type: SignalType;
  stage: SignalStage;
  regime: Regime;
  rsi_1h: number;
  rsi_4h: number;
  price: number;
  strength: number;
}

export interface PositionSizingData {
  size_notional: number;
  size_contracts: number;
  leverage: number;
  risk_amount: number;
  risk_pct: number;
}

export interface OrderDetail {
  order_id: string;
  venue_order_id: string | null;
  symbol: string;
  side: OrderSide;
  status: OrderStatus;
  size: number;
  filled_size: number;
  remaining: number;
  price: number | null;
  created_at: string;
}

export interface OrderListItem {
  order_id: string;
  symbol: string;
  side: OrderSide;
  status: OrderStatus;
  size: number;
  filled_size: number;
}

export interface OrderListResponse {
  orders: OrderListItem[];
  count: number;
}

export interface ReconcileResponse {
  is_clean: boolean;
  order_discrepancies: number;
  position_discrepancies: number;
  details: Record<string, unknown>;
}

export interface RiskLimitsResponse {
  max_leverage: number;
  risk_per_trade_min: number;
  risk_per_trade_max: number;
  max_total_exposure_pct: number;
  universe: string[];
}

export interface PositionSizeRequest {
  equity: number;
  entry_price: number;
  stop_price: number;
  direction: "long" | "short";
  current_exposure: number;
  max_leverage: number;
  method: "fixed_fractional" | "quarter_kelly";
  win_rate?: number;
  avg_win_loss_ratio?: number;
}

export interface PositionSizeResponse {
  size_notional: number;
  size_contracts: number;
  leverage: number;
  risk_amount: number;
  risk_pct: number;
  margin_required: number;
}

export interface VaRRequest {
  returns: number[];
  method: "historical" | "parametric";
}

export interface VaRResponse {
  var_95: number;
  var_99: number;
  cvar_95: number;
  method: string;
}

export interface PerformanceReport {
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  avg_r_multiple: number;
  period: string;
}

export interface ExceptionClassifyRequest {
  exception_type: string;
  market_context: Record<string, unknown>;
  signal_data: Record<string, unknown>;
}

export interface ExceptionClassifyResponse {
  category: string | null;
  confidence: number | null;
  explanation: string | null;
  recommended_action: string | null;
  error: string | null;
}

// ─── Dashboard display types (front-end only) ────────────

export interface OpenPosition {
  id: string;
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  current_price: number | null;
  stop_loss: number | null;
  unrealized_pnl: number;
  realized_pnl: number;
  leverage: number;
  partial_exited: boolean;
  be_moved: boolean;
  opened_at: string | null;
}

export interface OpenPositionsResponse {
  positions: OpenPosition[];
  count: number;
}

export interface MarketData {
  symbol: string;
  markPrice: number;
  spread: number;
  rsi_4h: number;
  rsi_1h: number;
  rsi_15m: number;
  regime: Regime;
  bidSize: number;
  askSize: number;
  lastUpdate: number;
}

export interface RiskDisplay {
  notional: number;
  realLeverage: number;
  freeMargin: number;
  varIntraday: number;
  mddRolling: number;
  dailyLimitConsumed: number;
}

export interface ExecutionDisplay {
  fillRatio: number;
  avgSlippage: number;
  fundingRate: number;
  latencyP50: number;
  latencyP95: number;
  latencyP99: number;
}

export interface ComplianceDisplay {
  walletConnected: boolean;
  keyStatus: "active" | "expired" | "revoked";
  ipAllowlisted: boolean;
  logRetentionDays: number;
}

export interface EquityPoint {
  date: string;
  equity: number;
}

export interface DrawdownPoint {
  date: string;
  drawdown: number;
}

export interface SignalHistoryEntry {
  id: string;
  timestamp: string;
  type: SignalType;
  stage: SignalStage;
  regime: Regime;
  rsi_1h: number;
  rsi_4h: number;
  price: number;
  strength: number;
}

export interface TradeDistributionPoint {
  range: string;
  count: number;
}
