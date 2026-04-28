import { useQuery } from "@tanstack/react-query";
import { getRiskLimits } from "@/api/risk";
import { listOrders } from "@/api/orders";

export function useRiskLimits() {
  return useQuery({
    queryKey: ["riskLimits"],
    queryFn: getRiskLimits,
    refetchInterval: 30000,
  });
}

export function useActiveOrders(symbol?: string) {
  return useQuery({
    queryKey: ["orders", symbol],
    queryFn: () => listOrders(symbol),
    refetchInterval: 5000,
  });
}
