import { get, post } from "./client";
import type { SignalEvaluateRequest, SignalEvaluateResponse, BotStatusResponse } from "@/types";

export function evaluateSignal(req: SignalEvaluateRequest) {
  return post<SignalEvaluateResponse>("/v1/signals/evaluate", req);
}

export function getBotStatus() {
  return get<BotStatusResponse>("/v1/signals/bot-status");
}
