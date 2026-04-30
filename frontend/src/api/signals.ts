import { get, post } from "./client";
import type { SignalEvaluateRequest, SignalEvaluateResponse, BotStatusResponse, BotLogResponse } from "@/types";

export function evaluateSignal(req: SignalEvaluateRequest) {
  return post<SignalEvaluateResponse>("/v1/signals/evaluate", req);
}

export function getBotStatus() {
  return get<BotStatusResponse>("/v1/signals/bot-status");
}

export function startBot() {
  return post<{ status: string }>("/v1/signals/bot-start");
}

export function stopBot() {
  return post<{ status: string }>("/v1/signals/bot-stop");
}

export function getBotLogs() {
  return get<BotLogResponse>("/v1/signals/bot-logs?limit=100");
}
