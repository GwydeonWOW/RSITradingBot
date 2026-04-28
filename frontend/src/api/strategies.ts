import { get, post } from "./client";
import type {
  BacktestRequest,
  BacktestResponse,
  BacktestDetailResponse,
  BacktestListResponse,
  WalkForwardRequest,
} from "@/types";

export function runBacktest(req: BacktestRequest) {
  return post<BacktestResponse>("/v1/strategies/rsi/backtests", req);
}

export function runWalkForward(req: WalkForwardRequest) {
  return post<Record<string, unknown>>("/v1/strategies/rsi/walkforward", req);
}

export function getBacktestResult(resultId: string) {
  return get<BacktestDetailResponse>(`/v1/strategies/rsi/backtests/${resultId}`);
}

export function listBacktests() {
  return get<BacktestListResponse>("/v1/strategies/rsi/backtests");
}
