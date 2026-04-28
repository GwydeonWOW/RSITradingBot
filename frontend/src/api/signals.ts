import { post } from "./client";
import type { SignalEvaluateRequest, SignalEvaluateResponse } from "@/types";

export function evaluateSignal(req: SignalEvaluateRequest) {
  return post<SignalEvaluateResponse>("/v1/signals/evaluate", req);
}
