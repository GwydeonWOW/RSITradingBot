import { get } from "./client";

export function getPerformanceSummary() {
  return get<Record<string, unknown>>("/v1/reports/performance");
}
