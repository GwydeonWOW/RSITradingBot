import { get, post } from "./client";
import type {
  RiskLimitsResponse,
  PositionSizeRequest,
  PositionSizeResponse,
  VaRRequest,
  VaRResponse,
} from "@/types";

export function getRiskLimits() {
  return get<RiskLimitsResponse>("/v1/risk/limits");
}

export function calculatePositionSize(req: PositionSizeRequest) {
  return post<PositionSizeResponse>("/v1/risk/limits/position-size", req);
}

export function calculateVaR(req: VaRRequest) {
  return post<VaRResponse>("/v1/risk/limits/var", req);
}
