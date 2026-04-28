import { get, post } from "./client";
import type {
  OrderSubmitRequest,
  OrderSubmitResponse,
  OrderDetail,
  OrderListResponse,
  ReconcileResponse,
} from "@/types";

export function submitOrder(req: OrderSubmitRequest) {
  return post<OrderSubmitResponse>("/v1/orders/submit", req);
}

export function getOrder(orderId: string) {
  return get<OrderDetail>(`/v1/orders/${orderId}`);
}

export function listOrders(symbol?: string) {
  const params = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  return get<OrderListResponse>(`/v1/orders/${params}`);
}

export function reconcileOrders() {
  return post<ReconcileResponse>("/v1/orders/reconcile");
}
